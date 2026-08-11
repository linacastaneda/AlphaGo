/* Navegación entre pestañas (Partida / Replay / Métricas) y soporte de hash. */

(() => {
  const botones = document.querySelectorAll(".nav__boton");
  const nombres = Array.from(botones).map((b) => b.dataset.pestana);

  window.mostrarPestana = function mostrar(nombre) {
    if (!nombres.includes(nombre)) return;
    for (const b of botones) b.classList.toggle("activo", b.dataset.pestana === nombre);
    for (const n of nombres) {
      document.getElementById(`pestana-${n}`).classList.toggle("oculta", n !== nombre);
    }
    try { history.replaceState(null, "", `#${nombre}`); } catch (_e) { location.hash = nombre; }
    document.dispatchEvent(new CustomEvent("pestana:mostrada", { detail: nombre }));
  };

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