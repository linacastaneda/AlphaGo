/* Navegación entre pestañas (Partida / Replay / Métricas) y soporte de hash. */

(() => {
  const botones = document.querySelectorAll(".nav__boton[data-pestana]");
  const nombres = Array.from(botones).map((b) => b.dataset.pestana);

  function mostrar(nombre) {
    if (!nombres.includes(nombre)) return;
    for (const b of botones) b.classList.toggle("activo", b.dataset.pestana === nombre);
    for (const n of nombres) {
      document.getElementById(`pestana-${n}`).classList.toggle("oculta", n !== nombre);
    }
    // conserva la query (?partida=ID) solo si el destino es replay
    const esReplay = nombre === "replay" && location.hash.indexOf("?") >= 0;
    const nuevoHash = esReplay ? location.hash : `#${nombre}`;
    try { history.replaceState(null, "", nuevoHash); } catch (_e) { location.hash = nuevoHash; }
    document.dispatchEvent(new CustomEvent("pestana:mostrada", { detail: nombre }));
  }
  window.mostrarPestana = mostrar;

  botones.forEach((b) => {
    b.addEventListener("click", () => {
      mostrar(b.dataset.pestana);
      window.scrollTo({ top: 0 });
    });
  });

  function pestana_actual() {
    return (location.hash || "#partida").slice(1).split("?")[0];
  }

  window.addEventListener("hashchange", () => mostrar(pestana_actual()));

  mostrar(pestana_actual());
})();
// === Sistema de Sonido (Madera / Go) ===
(() => {
  const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  
  // Desbloquear audio en el primer clic del usuario
  document.addEventListener("click", () => {
    if (audioCtx.state === "suspended") audioCtx.resume();
  }, { once: true });

  let sonidoActivo = true;
  const botonSonido = document.getElementById("boton-sonido");
  if (botonSonido) {
    botonSonido.addEventListener("click", () => {
      sonidoActivo = !sonidoActivo;
      botonSonido.textContent = sonidoActivo ? "🔊" : "🔇";
      botonSonido.title = sonidoActivo ? "Desactivar sonido" : "Activar sonido";
    });
  }

  window.reproducirSonidoPiedra = function() {
    if (!sonidoActivo || audioCtx.state === "suspended") return;
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    
    osc.type = "sine";
    osc.frequency.setValueAtTime(600, audioCtx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(150, audioCtx.currentTime + 0.06);
    
    gain.gain.setValueAtTime(0, audioCtx.currentTime);
    gain.gain.linearRampToValueAtTime(1, audioCtx.currentTime + 0.01);
    gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.06);
    
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    osc.start();
    osc.stop(audioCtx.currentTime + 0.06);
  };
})();
