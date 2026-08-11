/* Métricas: rankings, IA y latencia desde /api/metrics y /api/perf. */

(() => {
  const _set = (id, valor) => { const el = document.getElementById(id); if (el) el.textContent = valor !== undefined && valor !== null ? valor : "—"; };

  async function cargar_metrics() {
    try {
      const respuesta = await fetch("/api/metrics");
      const datos = await respuesta.json();
      rendir_rankings(datos.rankings || []);
      rendir_ia(datos.estadisticas_ia || []);
      rendir_winrate(datos.rankings || []);
    } catch (err) {
      const tb = document.getElementById("tabla-rankings");
      if (tb) tb.querySelector("tbody").innerHTML = `<tr><td colspan="4">Error: ${err.message}</td></tr>`;
    }
  }

  function rendir_rankings(rankings) {
    const tabla = document.getElementById("tabla-rankings");
    const cuerpoJ = tabla ? tabla.querySelector("tbody") : null;
    if (!cuerpoJ) return;
    const filas = rankings.slice().sort((a, b) => b.victorias - a.victorias);
    cuerpoJ.innerHTML = filas.length
      ? filas.map((j) => {
          const tasa = j.partidas ? ((j.win_rate || 0) * 100).toFixed(0) : "—";
          return `<tr><td>${j.jugador}</td><td>${j.victorias}</td><td>${j.derrotas}</td><td>${tasa}%</td></tr>`;
        }).join("")
      : `<tr><td colspan="4">Sin partidas registradas</td></tr>`;
  }

  function rendir_ia(estadisticas) {
    const tabla = document.getElementById("tabla-ia");
    const cuerpoI = tabla ? tabla.querySelector("tbody") : null;
    if (!cuerpoI) return;
    if (!estadisticas.length) {
      cuerpoI.innerHTML = `<tr><td colspan="5">Sin datos de configuraciones IA</td></tr>`;
      return;
    }
    cuerpoI.innerHTML = estadisticas.map((f) => {
      const sims = f.movimientos ? (f.sims / f.movimientos).toFixed(0) : "—";
      const ms = f.tiempo_promedio_ms != null ? f.tiempo_promedio_ms.toFixed(0) : "—";
      const sps = f.sims_por_segundo != null ? f.sims_por_segundo.toFixed(1) : "—";
      return `<tr><td>${f.config}</td><td>${f.movimientos}</td><td>${sims}</td><td>${ms}</td><td>${sps}</td></tr>`;
    }).join("");
  }

  function rendir_winrate(rankings) {
    const canvas = document.getElementById("graf-winrate");
    if (!canvas || typeof window.Chart === "undefined") return;
    const etiquetas = rankings.map((j) => j.jugador);
    const valores = rankings.map((j) => (j.win_rate || 0) * 100);
    if (window._winChart) window._winChart.destroy();
    window._winChart = new window.Chart(canvas, {
      type: "bar",
      data: {
        labels: etiquetas,
        datasets: [{
          label: "Win-rate (%)",
          data: valores,
          backgroundColor: "rgba(224, 176, 70, 0.55)",
          borderColor: "#e0b046",
          borderWidth: 1
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { color: "rgba(25,22,18,0.08)" }, ticks: { color: "#4a443a" } },
          y: { beginAtZero: true, max: 100, grid: { color: "rgba(25,22,18,0.08)" }, ticks: { color: "#4a443a" } }
        }
      }
    });
  }

  async function cargar_perf() {
    try {
      const respuesta = await fetch("/api/perf");
      const datos = await respuesta.json();
      _set("perf-total", datos.total_mediciones);
      _set("perf-mem", datos.memoria_promedio_kb ? `${(datos.memoria_promedio_kb / 1024).toFixed(0)} MB` : "—");
      _set("perf-memmax", datos.max_memoria_kb ? `${(datos.max_memoria_kb / 1024).toFixed(0)} MB` : "—");
      rendir_latencia(datos.endpoints || {});
    } catch (err) {
      // sin datos, quedan los guiones
    }
  }

  function rendir_latencia(endpoints) {
    const canvas = document.getElementById("graf-latencia");
    if (!canvas || typeof window.Chart === "undefined") return;
    const nombres = Object.keys(endpoints);
    const p95 = nombres.map((n) => endpoints[n].p95_ms !== undefined ? endpoints[n].p95_ms : 0);
    if (window._latChart) window._latChart.destroy();
    window._latChart = new window.Chart(canvas, {
      type: "bar",
      data: {
        labels: nombres,
        datasets: [{
          label: "p95 (ms)",
          data: p95,
          backgroundColor: "rgba(224, 176, 70, 0.55)",
          borderColor: "#e0b046",
          borderWidth: 1
        }]
      },
      options: {
        responsive: true,
        indexAxis: "y",
        plugins: { legend: { display: false } },
        scales: {
          x: { beginAtZero: true, grid: { color: "rgba(25,22,18,0.08)" }, ticks: { color: "#4a443a" } },
          y: { grid: { color: "rgba(25,22,18,0.08)" }, ticks: { color: "#4a443a" } }
        }
      }
    });
  }

  cargar_metrics();
  cargar_perf();

  document.addEventListener("pestana:mostrada", (ev) => {
    if (ev.detail === "metricas") {
      cargar_metrics();
      cargar_perf();
    }
  });
})();