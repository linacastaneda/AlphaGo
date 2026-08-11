/* Replay: menú de historial de partidas y reproducción por coordenadas. */

(() => {
  const svg = document.getElementById("tablero-replay");
  const contenedor = document.getElementById("contenedor-historial");
  const botonHistorial = document.getElementById("boton-historial");
  const menu = document.getElementById("menu-historial");
  const cerrarMenu = document.getElementById("historial-cerrar");
  const filtro = document.getElementById("filtro-historial");
  const lista = document.getElementById("lista-partidas");
  const contador = document.getElementById("contador-historial");
  const slider = document.getElementById("replay-slider");
  const progreso = document.getElementById("replay-progreso");
  const coordEl = document.getElementById("replay-coord");
  const captEl = document.getElementById("replay-capturas");
  const aiEl = document.getElementById("replay-ai");
  const velocidad = document.getElementById("replay-velocidad");
  const seleccion = document.getElementById("historial-seleccion");
  const titulo = document.getElementById("replay-titulo");
  const sub = document.getElementById("replay-sub");

  const LETRAS = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S"];
  let tablero = window.CrearTablero(svg, 9, () => {});
  let tamanoTablero = 9;
  tablero.redibujar({ tablero: Array.from({ length: 9 }, () => Array(9).fill(0)) }, { animar: false });

  function asegurarTablero(tamano) {
    if (tamano !== tamanoTablero) {
      tamanoTablero = tamano;
      tablero = window.CrearTablero(svg, tamano, () => {});
      tablero.redibujar(
        { tablero: Array.from({ length: tamano }, () => Array(tamano).fill(0)) },
        { animar: false });
    }
  }

  let partida = null;
  let movimientos = [];
  let indice = 0;
  let jugando = false;
  let temporizador = null;
  let partidasCache = [];
  let partidaCargada = null;

  /* ── Lógica de tablero (reconstrucción) ───────────────────── */

  function vecinos(f, c, tamano) {
    return [[f - 1, c], [f + 1, c], [f, c - 1], [f, c + 1]]
      .filter(([vf, vc]) => vf >= 0 && vf < tamano && vc >= 0 && vc < tamano);
  }

  function grupo_desde(m, f, c, color, tamano) {
    const grupo = new Set();
    const pila = [[f, c]];
    while (pila.length) {
      const [gf, gc] = pila.pop();
      const clave = `${gf}:${gc}`;
      if (grupo.has(clave)) continue;
      grupo.add(clave);
      for (const [vf, vc] of vecinos(gf, gc, tamano)) {
        if (m[vf][vc] === color && !grupo.has(`${vf}:${vc}`)) pila.push([vf, vc]);
      }
    }
    return grupo;
  }

  function capturar_grupos(m, fila, col, color, tamano) {
    const oponente = color === 1 ? 2 : 1;
    const eliminadas = new Set();
    for (const [vf, vc] of vecinos(fila, col, tamano)) {
      if (m[vf][vc] !== oponente) continue;
      const clave = `${vf}:${vc}`;
      if (eliminadas.has(clave)) continue;
      const grupo = grupo_desde(m, vf, vc, oponente, tamano);
      let libertades = 0;
      for (const pos of grupo) {
        const [gf, gc] = pos.split(":").map(Number);
        for (const [lf, lc] of vecinos(gf, gc, tamano)) {
          if (m[lf][lc] === 0) libertades++;
        }
      }
      if (libertades === 0) {
        for (const pos of grupo) {
          eliminadas.add(pos);
          const [gf, gc] = pos.split(":").map(Number);
          m[gf][gc] = 0;
        }
      }
    }
    return eliminadas.size;
  }

  function esNegro(mov) {
    const color = mov.player || mov.color;
    return color === "B" || color === 1 || color === "1";
  }

  function reconstruir(tamano, listaMovs) {
    const m = Array.from({ length: tamano }, () => Array(tamano).fill(0));
    let ultimo = null;
    for (const mov of listaMovs) {
      if (mov.tipo !== "jugada") continue;
      const color = esNegro(mov) ? 1 : 2;
      const [f, c] = mov.coord;
      m[f][c] = color;
      capturar_grupos(m, f, c, color, tamano);
      ultimo = [f, c];
    }
    return { m, ultimo };
  }

  let indiceAnterior = 0;

  function mostrar(indiceMostrar) {
    if (!partida) return;
    if (indiceMostrar > indiceAnterior && window.reproducirSonidoPiedra) {
      window.reproducirSonidoPiedra();
    }
    indiceAnterior = indiceMostrar;
    const tamano = partida.board_size || partida.tamano || 9;
    asegurarTablero(tamano);
    const { m, ultimo } = reconstruir(tamano, movimientos.slice(0, indiceMostrar));
    tablero.redibujar({ tablero: m }, { ultimo, animar: false });

    slider.value = indiceMostrar;
    slider.max = movimientos.length;
    progreso.textContent = `${indiceMostrar} / ${movimientos.length}`;

    const mov = movimientos[indiceMostrar - 1];
    if (!mov) {
      coordEl.textContent = "posición inicial";
      captEl.textContent = "";
      aiEl.textContent = "";
      return;
    }
    const turno = esNegro(mov) ? "● negro" : "○ blanco";
    coordEl.textContent = mov.tipo === "pase"
      ? `mov ${indiceMostrar} · ${turno} · PASO`
      : `mov ${indiceMostrar} · ${turno} · ${LETRAS[mov.coord[1]]}${mov.coord[0] + 1}`;
    captEl.textContent = mov.capturas ? `+${mov.capturas} captura/s` : "";
    if (mov.ai) {
      const ai = mov.ai;
      aiEl.textContent = `IA ${(ai.config || "").replace("mcts-", "")} sims · ${Math.round(ai.time_ms || 0)} ms · win ${((ai.win_rate || 0) * 100).toFixed(0)}%`;
    } else {
      aiEl.textContent = "";
    }
  }

  /* ── Controles de reproducción ────────────────────────────── */

  function detener() {
    jugando = false;
    if (temporizador) { clearInterval(temporizador); temporizador = null; }
    document.getElementById("replay-play").textContent = "▶";
  }

  function reproducir() {
    if (!partida || movimientos.length === 0) return;
    if (jugando) { detener(); return; }
    if (indice >= movimientos.length) indice = 0;
    jugando = true;
    document.getElementById("replay-play").textContent = "❚❚";
    const velocidadMs = Number(velocidad.value);
    temporizador = setInterval(() => {
      if (indice >= movimientos.length) { detener(); return; }
      indice++;
      mostrar(indice);
    }, velocidadMs);
  }

  /* ── Carga de una partida ─────────────────────────────────── */

  function resumen_ganador(datos) {
    const resultado = datos.resultado || {};
    if (datos.terminada === false && !resultado.ganador) return "en curso";
    if (resultado.ganador == null) return "empate";
    const simbolo = resultado.ganador === 1 ? "B" : resultado.ganador === 2 ? "W" : String(resultado.ganador);
    const jugador = (datos.jugadores || {})[simbolo] || "?";
    return `${simbolo === "B" ? "●" : "○"} ${jugador} gana`;
  }

  async function cargar(identificador) {
    detener();
    try {
      const respuesta = await fetch(`/api/game/${identificador}`);
      if (!respuesta.ok) throw new Error(`HTTP ${respuesta.status}`);
      partida = await respuesta.json();
      movimientos = partida.movimientos || [];
      indice = 0;
      partidaCargada = identificador;

      const jug = partida.jugadores || {};
      const fecha = new Date(partida.fecha || Date.now());
      titulo.textContent = `${resumen_ganador(partida)} — ${jug.B || "?"} vs ${jug.W || "?"}`;
      sub.textContent = `${movimientos.length} movimientos · ${partida.board_size || partida.tamano || 9}×${(partida.board_size || partida.tamano || 9)} · ${fecha.toLocaleString("es")}`;
      seleccion.querySelector(".historial-seleccion__texto").textContent =
        `● ${jug.B || "?"} vs ○ ${jug.W || "?"} · ${movimientos.length} movs · ${fecha.toLocaleDateString("es")}`;

      marcarSeleccionada(identificador);
      cerrarMenuYFiltro();
      mostrar(0);
    } catch (err) {
      aiEl.textContent = `no se pudo cargar: ${err.message}`;
    }
  }

  /* ── Menú de historial ────────────────────────────────────── */

  function abrirMenu() {
    contenedor.classList.add("abierto");
    menu.classList.remove("oculta");
  }

  function cerrarMenuYFiltro() {
    contenedor.classList.remove("abierto");
    menu.classList.add("oculta");
    filtro.value = "";
    rendirLista(partidasCache);
  }

  function alternarMenu() {
    const cerrado = menu.classList.contains("oculta");
    if (cerrado) { abrirMenu(); filtro.focus(); } else { cerrarMenuYFiltro(); }
  }

  function marcarSeleccionada(id) {
    for (const hijo of lista.children) hijo.classList.remove("seleccionada");
    const li = lista.querySelector(`[data-id="${id}"]`);
    if (li) li.classList.add("seleccionada");
  }

  function texto_partida(p) {
    const jug = p.jugadores || {};
    const fecha = new Date(p.fecha || Date.now());
    const marca = p.ganador === "B" ? "●" : p.ganador === "W" ? "○" : "—";
    return `${marca} ${jug.B || "?"} vs ${jug.W || "?"} ${p.tablero}x${p.tablero} ${fecha.toLocaleDateString("es")}`;
  }

  function filtrar_partidas(texto) {
    const q = texto.trim().toLowerCase();
    if (!q) return partidasCache;
    return partidasCache.filter((p) => {
      const jug = p.jugadores || {};
      const base = `${p.id} ${jug.B || ""} ${jug.W || ""} ${p.tablero} ${texto_partida(p)}`;
      return base.toLowerCase().includes(q);
    });
  }

  function rendirLista(partidas) {
    lista.innerHTML = "";
    if (partidas.length === 0) {
      const li = document.createElement("li");
      li.textContent = partidasCache.length
        ? "Sin resultados para el filtro."
        : "Aún no hay partidas guardadas.";
      li.style.cursor = "default";
      lista.appendChild(li);
      return;
    }
    for (const p of partidas) {
      const li = document.createElement("li");
      li.dataset.id = p.id;
      const cab = document.createElement("div");
      cab.className = "item-sgf__cab";
      const fecha = new Date(p.fecha || Date.now());
      cab.innerHTML = `<span>${(p.ganador === "B" ? "●" : p.ganador === "W" ? "○" : "—")} ${p.jugadores.B || "?"} vs ${p.jugadores.W || "?"}</span><span>${fecha.toLocaleDateString("es")}</span>`;
      const meta = document.createElement("div");
      meta.className = "item-sgf__meta";
      meta.textContent = `${p.num_movimientos} movimientos · ${p.tablero}x${p.tablero}`;
      li.appendChild(cab);
      li.appendChild(meta);
      li.addEventListener("click", () => cargar(p.id));
      lista.appendChild(li);
    }
    if (partidaCargada) marcarSeleccionada(partidaCargada);
  }

  async function listar() {
    try {
      const respuesta = await fetch("/api/games");
      const datos = await respuesta.json();
      partidasCache = datos.partidas || [];
      contador.textContent = partidasCache.length;
      rendirLista(filtrar_partidas(filtro.value));
    } catch (err) {
      contador.textContent = "0";
      lista.innerHTML = `<li>Error listando partidas: ${err.message}</li>`;
    }
  }

  function cargarDesdeHash() {
    const enlazada = (location.hash.match(/partida=([\w-]+)/) || [])[1];
    if (enlazada) cargar(enlazada);
    else if (!partidaCargada) abrirMenu();
  }

  /* ── Eventos ──────────────────────────────────────────────── */

  botonHistorial.addEventListener("click", alternarMenu);
  cerrarMenu.addEventListener("click", cerrarMenuYFiltro);
  filtro.addEventListener("input", () => rendirLista(filtrar_partidas(filtro.value)));
  filtro.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape") cerrarMenuYFiltro();
  });
  document.addEventListener("click", (ev) => {
    // el botón de pestaña abre el menú al entrar; no debe cerrarse por el mismo click
    if (ev.target.closest && ev.target.closest(".cabecera__nav")) return;
    if (!contenedor.contains(ev.target) && !menu.classList.contains("oculta")) {
      cerrarMenuYFiltro();
    }
  });

  document.getElementById("replay-inicio").addEventListener("click", () => { detener(); indice = 0; mostrar(0); });
  document.getElementById("replay-atras").addEventListener("click", () => {
    detener();
    if (indice > 0) { indice--; mostrar(indice); }
  });
  document.getElementById("replay-siguiente").addEventListener("click", () => {
    detener();
    if (indice < movimientos.length) { indice++; mostrar(indice); }
  });
  document.getElementById("replay-play").addEventListener("click", reproducir);
  slider.addEventListener("input", () => { detener(); indice = Number(slider.value); mostrar(indice); });
  velocidad.addEventListener("change", () => { if (jugando) { detener(); reproducir(); } });

  document.addEventListener("pestana:mostrada", (ev) => {
    if (ev.detail !== "replay") {
      detener();
      return;
    }
    listar();
    cargarDesdeHash();
  });

  /* Al cargar la página: si ya estamos en replay, prepara el historial. */
  if ((location.hash || "#partida").slice(1).split("?")[0] === "replay") {
    listar();
    cargarDesdeHash();
  }
})();
