/* Gestión de la partida en curso: llamadas a la API, turnos y KPIs. */

(() => {
  const svgTablero = document.getElementById("tablero");
  const estado = {
    id: null,
    modo: null,
    jugadores: {},
    tamano: 9,
    tablero: null,
    turno: null,
    ocupado: false,
    terminada: false,
  };

  const elems = {
    modo: document.getElementById("select-modo"),
    sims: document.getElementById("select-sims"),
    dueloOpciones: document.getElementById("duelo-opciones"),
    dueloNegro: document.getElementById("select-duelo-negro"),
    dueloBlanco: document.getElementById("select-duelo-blanco"),
    botonNueva: document.getElementById("boton-nueva"),
    botonPasar: document.getElementById("boton-pasar"),
    botonRendirse: document.getElementById("boton-rendirse"),
    botonPasoIa: document.getElementById("boton-paso-ia"),
    mensaje: document.getElementById("mensaje"),
    textoTurno: document.getElementById("texto-turno"),
    capturasNegro: document.getElementById("capturas-negro"),
    capturasBlanco: document.getElementById("capturas-blanco"),
    kpiJugada: document.getElementById("kpi-jugada"),
    kpiUltima: document.getElementById("kpi-ultima"),
    kpiCapturas: document.getElementById("kpi-capturas"),
    kpiResultado: document.getElementById("kpi-resultado"),
    iaNodos: document.getElementById("ia-nodos"),
    iaTiempo: document.getElementById("ia-tiempo"),
    iaWinrate: document.getElementById("ia-winrate"),
    barraWin: document.getElementById("barra-winrate"),
    indicador: document.getElementById("indicador-turno"),
  };

  const tablero = window.CrearTablero(svgTablero, 9, (fila, col) => elegir(fila, col), (fila, col) => hover(fila, col));

  function hover(fila, col) {
    if (!miTurno || estado.ocupado || estado.terminada) return;
    if (estado.tablero && estado.tablero[fila] && estado.tablero[fila][col] === 0) {
      tablero.resaltar(fila, col);
    } else {
      tablero.ocultarHover();
    }
  }

  let miTurno = false;

  async function api(ruta, opciones = {}) {
    const respuesta = await fetch(ruta, {
      headers: { "Content-Type": "application/json" },
      ...opciones,
    });
    const cuerpo = respuesta.ok ? await respuesta.json() : { error: `${respuesta.status}` };
    if (!respuesta.ok) throw new Error(cuerpo.error || `error ${respuesta.status}`);
    return cuerpo;
  }

  function mensaje(texto, esError = false) {
    elems.mensaje.textContent = texto;
    elems.mensaje.classList.toggle("error", esError);
  }

  const enlaceReplay = document.getElementById("enlace-replay");
  function mostrar_enlace_replay(id) {
    if (!enlaceReplay) return;
    if (id) {
      enlaceReplay.href = `#replay?partida=${id}`;
      enlaceReplay.classList.remove("oculta");
    } else {
      enlaceReplay.classList.add("oculta");
    }
  }

  const analisisEl = {
    tarjeta: document.getElementById("tarjeta-analisis"),
    lista: document.getElementById("lista-analisis"),
    nota: document.getElementById("analisis-nota"),
    boton: document.getElementById("boton-analizar"),
  };

  function limpiar_analisis() {
    if (!analisisEl.tarjeta) return;
    analisisEl.tarjeta.classList.add("oculta");
    analisisEl.lista.innerHTML = "";
    tablero.limpiarCandidatos();
  }

  function cargar_analisis() {
    if (!estado.id || estado.terminada || estado.ocupado) return;
    analisisEl.boton.disabled = true;
    analisisEl.lista.innerHTML = "<li class=\"lista-analisis__espera\">Analizando…</li>";
    analisisEl.tarjeta.classList.remove("oculta");
    api(`/api/game/${estado.id}/analysis`, {
      method: "POST",
      body: JSON.stringify({ simulaciones: elems.sims.value, top: 5 }),
    })
      .then((datos) => {
        const analisis = datos.analisis;
        const turno = datos.turno === "B" ? "● negro" : "○ blanco";
        analisisEl.nota.textContent = `${turno} · MCTS ${analisis.sims} sims · ${Math.round(analisis.tiempo_total_ms || 0)} ms · ${analisis.nodes} nodos`;
        const maxVisitas = Math.max(1, ...analisis.opciones.map((o) => o.visitas));
        analisisEl.lista.innerHTML = analisis.opciones.map((o, i) => {
          const win = Math.round((o.win_rate || 0) * 100);
          const coordTxt = o.pase ? "PASO" : `${LETRAS[o.col]}${o.fila + 1}`;
          return `
            <li class="lista-analisis__fila ${i === 0 ? "mejor" : ""}">
              <span class="lista-analisis__num">${i + 1}</span>
              <span class="lista-analisis__coord mono">${coordTxt}</span>
              <span class="lista-analisis__barra"><span class="lista-analisis__relleno" style="width:${(o.visitas / maxVisitas) * 100}%"></span></span>
              <span class="lista-analisis__win mono">${win}%</span>
            </li>`;
        }).join("");
        tablero.marcarCandidatos(analisis.opciones);
      })
      .catch((err) => {
        analisisEl.nota.textContent = err.message;
        analisisEl.lista.innerHTML = "";
      })
      .finally(() => { analisisEl.boton.disabled = false; });
  }

  function color_a_texto(color) {
    return color === 1 ? "Negro" : "Blanco";
  }

  function nombre_jugador(color) {
    const simbolo = color === 1 ? "B" : "W";
    const config = estado.jugadores[simbolo] || "humano";
    if (config === "humano") return "Humano";
    if (config.startsWith("mcts-l-")) return `MCTS L ${config.replace(/^mcts-l-/, "")} sims`;
    return config.replace(/^mcts-/, "MCTS ");
  }

  function jugador_en_turno() {
    const simbolo = estado.turno === 1 ? "B" : "W";
    return estado.jugadores[simbolo] || "humano";
  }

  function es_ia_en_turno() {
    return /^(mcts|alphago|ia)/.test(jugador_en_turno());
  }

  function ultimo_coord(estadoPartida) {
    const movs = estadoPartida.movimientos || [];
    for (let i = movs.length - 1; i >= 0; i--) {
      if (movs[i].tipo === "jugada") return movs[i].coord;
    }
    return null;
  }

  let movimientosAnteriores = 0;

  function renderizar(datos) {
    limpiar_analisis();
    if (estado.id !== datos.id) {
      movimientosAnteriores = datos.num_movimientos;
    } else if (datos.num_movimientos > movimientosAnteriores && window.reproducirSonidoPiedra) {
      window.reproducirSonidoPiedra();
      movimientosAnteriores = datos.num_movimientos;
    }
    estado.id = datos.id;
    estado.modo = datos.modo;
    estado.jugadores = datos.jugadores;
    estado.tamano = datos.tamano;
    estado.tablero = datos.tablero;
    estado.turno = datos.turno;
    estado.terminada = datos.terminada;

    tablero.redibujar(datos, { ultimo: ultimo_coord(datos) });

    elems.capturasNegro.textContent = (datos.capturas || {})[1] || 0;
    elems.capturasBlanco.textContent = (datos.capturas || {})[2] || 0;
    elems.kpiJugada.textContent = `${datos.num_movimientos} movs`;
    elems.kpiCapturas.textContent = `● ${elems.capturasNegro.textContent} · ○ ${elems.capturasBlanco.textContent}`;

    const ult = ultimo_coord(datos);
    elems.kpiUltima.textContent = ult
      ? `${LETRAS[ult[1]]}${ult[0] + 1}`
      : "—";

    // indicador de turno
    const piedra = elems.indicador.querySelector(".indicador-turno__piedra");
    if (datos.terminada) {
      piedra.className = "indicador-turno__piedra";
      elems.textoTurno.textContent = resultado_texto(datos.resultado);
      elems.kpiResultado.textContent = resultado_texto(datos.resultado);
    } else {
      piedra.className = `indicador-turno__piedra ${datos.turno === 1 ? "negra" : "blanca"}`;
      elems.textoTurno.textContent = `${color_a_texto(datos.turno)} juega`;
      elems.kpiResultado.textContent = "—";
    }

    const ultimoMov = (datos.movimientos || []).slice(-1)[0];
    actualizar_kpi_ia(ultimoMov && ultimoMov.ai);

    const esMiTurno = turno_humano_activo();
    miTurno = esMiTurno;
    if (!esMiTurno) tablero.ocultarHover();
    actualizar_botones();
  }

  function nombre_modo(modo) {
    return { pvp: "dos jugadores", vs_ia: "humano vs IA", ia_ia: "IA vs IA", duelo: "duelo MCTS vs MCTS L" }[modo] || modo;
  }

  function resultado_texto(resultado) {
    if (!resultado) return "—";
    if (!resultado.ganador) return "empate";
    const ganador = resultado.ganador === 1 ? "Negro" : "Blanco";
    if (resultado.por_rendicion) return `${ganador} gana por rendición`;
    const margen = resultado.margen != null ? ` por ${resultado.margen}` : "";
    return `${ganador} gana${margen}`;
  }

  function actualizar_kpi_ia(ai) {
    if (!ai) {
      elems.iaNodos.textContent = "—";
      elems.iaTiempo.textContent = "—";
      elems.iaWinrate.textContent = "—";
      elems.barraWin.style.width = "0%";
      return;
    }
    elems.iaNodos.textContent = ai.nodes != null ? ai.nodes : "—";
    elems.iaTiempo.textContent = ai.time_ms != null ? `${Math.round(ai.time_ms)} ms` : "—";
    elems.iaWinrate.textContent = ai.win_rate != null ? `${(ai.win_rate * 100).toFixed(1)}%` : "—";
    const win = ai.win_rate != null ? ai.win_rate : 0;
    elems.barraWin.style.width = `${(win * 100).toFixed(1)}%`;
  }

  function actualizar_botones() {
    const enCurso = estado.id && !estado.terminada;
    elems.botonPasar.disabled = !enCurso;
    elems.botonRendirse.disabled = !enCurso;
    elems.botonPasoIa.disabled = !enCurso || estado.ocupado;
    if (analisisEl.boton) analisisEl.boton.disabled = !enCurso;
  }

  function turno_humano_activo() {
    if (!estado.id || estado.terminada || estado.ocupado) return false;
    if (estado.modo === "pvp") return true;
    if (estado.modo === "vs_ia") return estado.turno === 1; // humano es negro
    if (estado.modo === "duelo") return !es_ia_en_turno();
    return false; // ia_ia: ningún humano en el tablero principal
  }

  function elegir(fila, col) {
    if (!turno_humano_activo() || estado.ocupado) return;
    estado.ocupado = true;
    api(`/api/game/${estado.id}/move`, {
      method: "POST",
      body: JSON.stringify({ fila, col }),
    })
      .then(procesarRespuesta)
      .catch((err) => {
        mensaje(err.message, true);
        estado.ocupado = false;
      });
  }

  function procesarRespuesta(cuerpo) {
    renderizar(cuerpo.estado);
    estado.ocupado = false;
    const datos = cuerpo.estado;
    if (datos.terminada) {
      mensaje(`Partida finalizada. ${resultado_texto(datos.resultado)} (guardada como ${datos.id})`);
      mostrar_enlace_replay(datos.id);
      return;
    }
    // si ahora le toca a una IA, juega sola
    const leTocaIa = (estado.modo === "vs_ia" && datos.turno === 2)
      || estado.modo === "ia_ia"
      || (estado.modo === "duelo" && es_ia_en_turno());
    if (leTocaIa) {
      mensaje(`La IA (${nombre_jugador(datos.turno)}) está pensando…`);
      window.setTimeout(movimiento_ia_automatico, 260);
    } else {
      mensaje("Coloca tu piedra en el tablero.");
    }
  }

  async function movimiento_ia_automatico() {
    if (estado.ocupado || !estado.id || estado.terminada) return;
    estado.ocupado = true;
    actualizar_botones();
    try {
      const datos = await api(`/api/game/${estado.id}/ai-move`, { method: "POST" });
      procesarRespuesta(datos);
    } catch (err) {
      mensaje(`IA: ${err.message}`, true);
      estado.ocupado = false;
      actualizar_botones();
    }
  }

  elems.botonNueva.addEventListener("click", async () => {
    elems.botonNueva.disabled = true;
    mostrar_enlace_replay(null);
    try {
      const cuerpo = {
        modo: elems.modo.value,
        simulaciones: elems.sims.value,
      };
      if (elems.modo.value === "duelo") {
        cuerpo.jugador_negro = elems.dueloNegro.value === "humano"
          ? "humano" : `${elems.dueloNegro.value}-${elems.sims.value}`;
        cuerpo.jugador_blanco = elems.dueloBlanco.value === "humano"
          ? "humano" : `${elems.dueloBlanco.value}-${elems.sims.value}`;
      }
      const datos = await api("/api/game/new", {
        method: "POST",
        body: JSON.stringify(cuerpo),
      });
      renderizar(datos);
      if (estado.modo === "ia_ia") {
        mensaje("IA vs IA: pulsa «Siguiente jugada IA» para avanzar paso a paso.");
        elems.botonPasoIa.disabled = false;
      } else if (estado.modo === "duelo") {
        mensaje(`Duelo: ${nombre_jugador(1)} vs ${nombre_jugador(2)}.`);
        if (es_ia_en_turno()) window.setTimeout(movimiento_ia_automatico, 300);
      } else if (estado.modo === "vs_ia") {
        mensaje("Negro juega primero: coloca tu piedra.");
      }
    } catch (err) {
      mensaje(err.message, true);
    } finally {
      elems.botonNueva.disabled = false;
    }
  });

  elems.modo.addEventListener("change", () => {
    if (elems.dueloOpciones) {
      elems.dueloOpciones.style.display = elems.modo.value === "duelo" ? "" : "none";
    }
  });
  if (elems.dueloOpciones) elems.dueloOpciones.style.display = "none";

  elems.botonPasar.addEventListener("click", async () => {
    if (estado.ocupado || !estado.id) return;
    estado.ocupado = true;
    try {
      const datos = await api(`/api/game/${estado.id}/pass`, { method: "POST" });
      procesarRespuesta(datos);
    } catch (err) {
      mensaje(err.message, true);
      estado.ocupado = false;
    }
  });

  elems.botonRendirse.addEventListener("click", async () => {
    if (!estado.id || !confirm("¿Confirmas la rendición?")) return;
    estado.ocupado = true;
    try {
      const color = estado.turno === 1 ? "B" : "W";
      const datos = await api(`/api/game/${estado.id}/resign`, {
        method: "POST",
        body: JSON.stringify({ color }),
      });
      renderizar(datos);
      mensaje(`Rendido. ${resultado_texto(datos.resultado)}`);
    } catch (err) {
      mensaje(err.message, true);
    } finally {
      estado.ocupado = false;
    }
  });

  elems.botonPasoIa.addEventListener("click", () => movimiento_ia_automatico());
  if (analisisEl.boton) analisisEl.boton.addEventListener("click", cargar_analisis);

  renderizar({ modo: "vs_ia", jugadores: {}, tamano: 9, turno: 1, terminada: true, tablero: Array.from({ length: 9 }, () => Array(9).fill(0)), capturas: { 1: 0, 2: 0 }, num_movimientos: 0, movimientos: [], resultado: null });
})
();