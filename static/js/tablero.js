/* Dibujo del tablero SVG, coordenadas, estrellas e interacción. */

const COLOR_PIEDRA = { 0: null, 1: "negro", 2: "blanco" };
const LETRAS = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S"];
const MARGEN = 70;
const LADO = 760;
let _consecutivoSvg = 0;

function _gradientes(svg) {
  /* Define gradientes radiales de piedra (negro sumi / blanco hueso) en un <defs>. */
  _consecutivoSvg += 1;
  const sufijo = _consecutivoSvg;
  const ns = "http://www.w3.org/2000/svg";
  const defs = document.createElementNS(ns, "defs");
  const crear = (id, paradas) => {
    const g = document.createElementNS(ns, "radialGradient");
    g.setAttribute("id", id);
    g.setAttribute("cx", "33%");
    g.setAttribute("cy", "30%");
    g.setAttribute("r", "85%");
    for (const [desfase, color] of paradas) {
      const s = document.createElementNS(ns, "stop");
      s.setAttribute("offset", desfase);
      s.setAttribute("stop-color", color);
      g.appendChild(s);
    }
    defs.appendChild(g);
  };
  crear(`piedra-negro-${sufijo}`, [["0%", "#2a2a2a"], ["45%", "#0a0a0a"], ["100%", "#000000"]]);
  crear(`piedra-blanco-${sufijo}`, [["0%", "#ffffff"], ["60%", "#eaeff5"], ["100%", "#d1d5db"]]);
  svg.insertBefore(defs, svg.firstChild);
  return {
    negro: `url(#piedra-negro-${sufijo})`,
    blanco: `url(#piedra-blanco-${sufijo})`,
  };
}

function hoshi_para(tamano) {
  const h = [];
  const puntos = tamano >= 13 ? [3, tamano - 4] : [2, tamano - 3];
  const centro = Math.floor(tamano / 2);
  for (const f of [puntos[0], centro, puntos[1]]) {
    for (const c of [puntos[0], centro, puntos[1]]) {
      if (f === centro && c === centro && tamano === 9) continue;
      h.push([f, c]);
    }
  }
  return h;
}

function _coord_a_pixel(fila, col, tamano) {
  const celda = (LADO - 2 * MARGEN) / (tamano - 1);
  return { x: MARGEN + col * celda, y: MARGEN + fila * celda };
}

function _normaSVG(svg) {
  const r = svg.getBoundingClientRect();
  return { escala: LADO / r.width, izquierda: r.left, arriba: r.top };
}

function crear_tablero(svg, tamano, alChasquido, alHover) {
  const celda = (LADO - 2 * MARGEN) / (tamano - 1);
  const radio = celda * 0.44;
  let ultimoEstado = null;

  const cuerpo = document.createElementNS("http://www.w3.org/2000/svg", "g");
  const grupoPiedras = document.createElementNS("http://www.w3.org/2000/svg", "g");
  const grupoMarcas = document.createElementNS("http://www.w3.org/2000/svg", "g");
  const grupoCandidatos = document.createElementNS("http://www.w3.org/2000/svg", "g");
  const hover = document.createElementNS("http://www.w3.org/2000/svg", "circle");
  svg.innerHTML = "";
  svg.appendChild(cuerpo);
  svg.appendChild(hover);
  svg.appendChild(grupoPiedras);
  svg.appendChild(grupoMarcas);
  svg.appendChild(grupoCandidatos);
  const rellenos = _gradientes(svg);

  const ns = "http://www.w3.org/2000/svg";
  for (let i = 0; i < tamano; i++) {
    const linea = document.createElementNS(ns, "line");
    linea.setAttribute("class", "tablero__linea");
    linea.setAttribute("x1", MARGEN + i * celda);
    linea.setAttribute("y1", MARGEN);
    linea.setAttribute("x2", MARGEN + i * celda);
    linea.setAttribute("y2", LADO - MARGEN);
    cuerpo.appendChild(linea);

    const linea2 = document.createElementNS(ns, "line");
    linea2.setAttribute("class", "tablero__linea");
    linea2.setAttribute("x1", MARGEN);
    linea2.setAttribute("y1", MARGEN + i * celda);
    linea2.setAttribute("x2", LADO - MARGEN);
    linea2.setAttribute("y2", MARGEN + i * celda);
    cuerpo.appendChild(linea2);
  }

  for (const [f, c] of hoshi_para(tamano)) {
    const p = _coord_a_pixel(f, c, tamano);
    const hoshi = document.createElementNS(ns, "circle");
    hoshi.setAttribute("class", "tablero__hoshi");
    hoshi.setAttribute("cx", p.x);
    hoshi.setAttribute("cy", p.y);
    hoshi.setAttribute("r", Math.max(4, celda * 0.10));
    cuerpo.appendChild(hoshi);
  }

  for (let c = 0; c < tamano; c++) {
    const t = document.createElementNS(ns, "text");
    t.setAttribute("class", "tablero__coord");
    t.setAttribute("x", MARGEN + c * celda);
    t.setAttribute("y", LADO - MARGEN / 2 + 6);
    t.textContent = LETRAS[c];
    cuerpo.appendChild(t);
  }
  for (let f = 0; f < tamano; f++) {
    const t = document.createElementNS(ns, "text");
    t.setAttribute("class", "tablero__coord");
    t.setAttribute("x", MARGEN / 2);
    t.setAttribute("y", MARGEN + f * celda + 6);
    t.textContent = f + 1;
    cuerpo.appendChild(t);
  }

  hover.setAttribute("class", "tablero__punto-hover");
  hover.setAttribute("r", radio * 0.9);
  hover.style.display = "none";

  function resaltar(fila, col) {
    if (fila === null || fila === undefined) {
      hover.style.display = "none";
      svg.style.cursor = "default";
      return;
    }
    const p = _coord_a_pixel(fila, col, tamano);
    hover.setAttribute("cx", p.x);
    hover.setAttribute("cy", p.y);
    hover.style.display = "block";
  }

  let previo = new Set();

  function redibujar(estado, opciones = {}) {
    ultimoEstado = estado;
    const animar = opciones.animar !== false;
    const tablero = estado.tablero || estado["tablero"] || [];

    grupoPiedras.innerHTML = "";
    const ns2 = "http://www.w3.org/2000/svg";
    const nuevoSet = new Set();
    for (let f = 0; f < tablero.length; f++) {
      const fila = tablero[f];
      for (let c = 0; c < fila.length; c++) {
        if (!fila[c]) continue;
        nuevoSet.add(`${f}:${c}`);
        const p = _coord_a_pixel(f, c, tamano);
        const circ = document.createElementNS(ns2, "circle");
        circ.setAttribute("class", `tablero__piedra ${COLOR_PIEDRA[fila[c]]}`);
        circ.setAttribute("fill", fila[c] === 1 ? rellenos.negro : rellenos.blanco);
        if (fila[c] === 2) {
          circ.setAttribute("stroke", "rgba(25,20,12,0.4)");
          circ.setAttribute("stroke-width", "1");
        }
        circ.setAttribute("cx", p.x);
        circ.setAttribute("cy", p.y);
        circ.setAttribute("r", radio);
        if (animar && !previo.has(`${f}:${c}`)) {
          circ.classList.add("nueva");
        }
        grupoPiedras.appendChild(circ);
      }
    }

    grupoMarcas.innerHTML = "";
    if (opciones.ultimo) {
      const [uf, uc] = opciones.ultimo;
      if (tablero[uf] && tablero[uf][uc]) {
        const p = _coord_a_pixel(uf, uc, tamano);
        const marca = document.createElementNS(ns2, "circle");
        const color = tablero[uf][uc] === 1 ? "blanco-mark" : "negro-mark";
        marca.setAttribute("class", `tablero__marca-ultima ${color}`);
        marca.setAttribute("cx", p.x);
        marca.setAttribute("cy", p.y);
        marca.setAttribute("r", Math.max(3.5, radio * 0.28));
        grupoMarcas.appendChild(marca);
      }
    }

    previo = nuevoSet;
  }

  svg.addEventListener("click", (ev) => {
    const n = _normaSVG(svg);
    const px = (ev.clientX - n.izquierda) * n.escala;
    const py = (ev.clientY - n.arriba) * n.escala;
    const fila = Math.round((py - MARGEN) / celda);
    const col = Math.round((px - MARGEN) / celda);
    if (fila >= 0 && fila < tamano && col >= 0 && col < tamano) {
      alChasquido(fila, col);
    }
  });

  if (alHover) {
    svg.addEventListener("mousemove", (ev) => {
      const n = _normaSVG(svg);
      const px = (ev.clientX - n.izquierda) * n.escala;
      const py = (ev.clientY - n.arriba) * n.escala;
      const fila = Math.round((py - MARGEN) / celda);
      const col = Math.round((px - MARGEN) / celda);
      if (fila >= 0 && fila < tamano && col >= 0 && col < tamano) {
        alHover(fila, col);
      } else {
        hover.style.display = "none";
      }
    });
    svg.addEventListener("mouseleave", () => { hover.style.display = "none"; });
  }

  function ocultarHover() { hover.style.display = "none"; }

  function marcarCandidatos(candidatos) {
    grupoCandidatos.innerHTML = "";
    const ns3 = "http://www.w3.org/2000/svg";
    candidatos.forEach((cand, indice) => {
      if (cand.pase) return;
      const p = _coord_a_pixel(cand.fila, cand.col, tamano);
      const texto = document.createElementNS(ns3, "text");
      texto.setAttribute("class", "tablero__candidato");
      texto.setAttribute("x", p.x);
      texto.setAttribute("y", p.y + 6);
      texto.textContent = String(indice + 1);
      grupoCandidatos.appendChild(texto);
    });
  }

  return { redibujar, resaltar, ocultarHover, marcarCandidatos, limpiarCandidatos: () => { grupoCandidatos.innerHTML = ""; } };
}

window.CrearTablero = crear_tablero;
window.Hoshi = hoshi_para;