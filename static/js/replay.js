/* Replay: lista de partidas guardadas y reproducción por coordenadas. */

(() => {
  const svg = document.getElementById("tablero-replay");
  const lista = document.getElementById("lista-partidas");
  const slider = document.getElementById("replay-slider");
  const progreso = document.getElementById("replay-progreso");
  const coordEl = document.getElementById("replay-coord");
  const captEl = document.getElementById("replay-capturas");
  const aiEl = document.getElementById("replay-ai");
  const velocidad = document.getElementById("replay-velocidad");

  const LETRAS = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S"];
  const tablero = window.CrearTablero(svg, 9, () => {});
  tablero.redibujar({ tablero: Array.from({ length: 9 }, () => Array(9).fill(0)) }, { animar: false });

  let partida = null;
  let movimientos = [];
  let indice = 0;
  let jugando = false;
  let temporizador = null;

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

  function reconstruir(tamano, listaMovs) {
    const m = Array.from({ length: tamano }, () => Array(tamano).fill(0));
    let ultimo = null;
    for (const mov of listaMovs) {
      if (mov.tipo !== "jugada") continue;
      const color = mov.color === "B" ? 1 : 2;
      const [f, c] = mov.coord;
      m[f][c] = color;
      capturar_grupos(m, f, c, color, tamano);
      ultimo = [f, c];
    }
    return { m, ultimo };
  }

  function mostrar(indiceMostrar) {
    if (!partida) return;
    const tamano = partida.board_size || partida.tamano || 9;
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
    const turno = (mov.player || mov.color) === "B" ? "● negro" : "○ blanco";
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

  async function cargar(identificador) {
    detener();
    try {
      const respuesta = await fetch(`/api/game/${identificador}`);
      partida = await respuesta.json();
      movimientos = partida.movimientos || [];
      indice = 0;
      mostrar(0);
    } catch (err) {
      aiEl.textContent = `no se pudo cargar: ${err.message}`;
    }
  }

  async function listar() {
    try {
      const respuesta = await fetch("/api/games");
      const datos = await respuesta.json();
      lista.innerHTML = "";
      const partidas = datos.partidas || [];
      if (partidas.length === 0) {
        const li = document.createElement("li");
        li.textContent = "Aún no hay partidas guardadas.";
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
        li.addEventListener("click", () => {
          seleccionar(li);
          cargar(p.id);
        });
        lista.appendChild(li);
      }
      const deseada = (location.hash.match(/partida=([\w-]+)/) || [])[1];
      if (deseada) {
        const li = lista.querySelector(`[data-id="${deseada}"]`);
        if (li) { seleccionar(li); cargar(deseada); }
      }
    } catch (err) {
      lista.innerHTML = `<li>Error listando partidas: ${err.message}</li>`;
    }
  }

  function seleccionar(li) {
    for (const hijo of lista.children) hijo.classList.remove("seleccionada");
    li.classList.add("seleccionada");
  }

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

  const listaCarga = listar();

  window.addEventListener("hashchange", () => {
    const enlazada = (location.hash.match(/partida=([\w-]+)/) || [])[1];
    if (!enlazada) return;
    listaCarga.then(() => {
      const li = lista.querySelector(`[data-id="${enlazada}"]`);
      if (li) seleccionar(li);
      cargar(enlazada);
    });
  });

  /* Al entrar en la pestaña Replay, refresca la lista (por si se guardaron
     partidas nuevas durante la sesión). */
  document.addEventListener("pestana:mostrada", (ev) => {
    if (ev.detail === "replay") listar();
  });
})();