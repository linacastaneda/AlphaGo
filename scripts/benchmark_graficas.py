"""Benchmark multi-motor: round-robin 7x7 entre todas las IAs y graficas.

Genera tres graficas PNG en la raiz del proyecto:
  - benchmark_winrate.png   : porcentaje de victorias por configuracion
  - benchmark_tiempo.png    : tiempo promedio por jugada
  - benchmark_sims.png      : simulaciones por segundo
  - benchmark_margen.png    : margen promedio de puntos

Uso:
    python -m scripts.benchmark_graficas            # con valores por defecto
    python -m scripts.benchmark_graficas --partidas 2 --tiempo 300
"""

import argparse
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from ia.torneo import torneo

CONFIGS = ["aleatorio", "mcts-250", "mcts-800", "mcts-l-250", "mcts-l-800"]
SALIDAS = {
    "winrate": "benchmark_winrate.png",
    "tiempo": "benchmark_tiempo.png",
    "sims": "benchmark_sims.png",
    "margen": "benchmark_margen.png",
}


def _grafica_barras(ruta, etiquetas, valores, titulo, etiqueta_y):
    fig, ax = plt.subplots(figsize=(9, 5))
    colores = ["#4c72b0", "#dd8452", "#55a868", "#c44e52", "#8172b2"]
    ax.bar(etiquetas, valores, color=colores[: len(etiquetas)])
    for i, v in enumerate(valores):
        ax.text(i, v, f"{v:.2f}", ha="center", va="bottom", fontsize=9)
    ax.set_ylabel(etiqueta_y)
    ax.set_title(titulo)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    fig.tight_layout()
    fig.savefig(ruta, dpi=150)
    plt.close(fig)


def generar_graficas(resumen):
    """Genera las graficas PNG a partir del resumen del torneo."""
    orden = list(resumen)
    etiquetas = [r["config"] for r in orden]

    winrates = [r["win_rate"] * 100 for r in orden]
    _grafica_barras(SALIDAS["winrate"], etiquetas, winrates,
                    "Win-rate por motor (round-robin 7x7)", "Win-rate (%)")

    tiempos = [r["tiempo_promedio_ms"] / 1000 for r in orden]
    _grafica_barras(SALIDAS["tiempo"], etiquetas, tiempos,
                    "Tiempo promedio por jugada (7x7)", "Segundos / jugada")

    sims = [r["sims_por_segundo"] for r in orden]
    _grafica_barras(SALIDAS["sims"], etiquetas, sims,
                    "Simulaciones por segundo (7x7)", "Sims / segundo")

    margenes = [r["margen_promedio"] if r["margen_promedio"] is not None else 0
                for r in orden]
    _grafica_barras(SALIDAS["margen"], etiquetas, margenes,
                    "Margen promedio de puntos (7x7)", "Puntos de margen")


def main():
    parser = argparse.ArgumentParser(description="Benchmark round-robin 7x7")
    parser.add_argument("--partidas", type=int, default=4)
    parser.add_argument("--tiempo", type=int, default=700,
                        help="tiempo limite por jugada en ms")
    parser.add_argument("--procesos", type=int, default=None)
    args = parser.parse_args()

    datos = torneo(configs=CONFIGS, partidas=args.partidas, tamano=7,
                   tiempo_limite_ms=args.tiempo, procesos=args.procesos)

    print("=== Enfrentamientos ===")
    for e in datos["enfrentamientos"]:
        print(" ", e)

    print("\n=== Resumen por configuracion ===")
    for r in datos["resumen"]:
        print(f"  {r['config']:<12} "
              f"G{r['victorias']} P{r['partidas']} "
              f"win={r['win_rate'] * 100:5.1f}% "
              f"margen={r['margen_promedio']} "
              f"tiempo={r['tiempo_promedio_ms']:6.1f}ms "
              f"sps={r['sims_por_segundo']:.1f}")

    generar_graficas(datos["resumen"])
    print("\nGraficas generadas:")
    for nombre, ruta in SALIDAS.items():
        print(f"  {ruta}")

    with open("data/benchmark_roundrobin.json", "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    print("\nResumen guardado en data/benchmark_roundrobin.json")


if __name__ == "__main__":
    main()
