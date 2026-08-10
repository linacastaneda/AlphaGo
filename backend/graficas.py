"""Gráficas para visualizar los resultados del benchmark MCTS."""

import matplotlib.pyplot as plt


def graficar_resultados_benchmark(resultados):
    """
    Genera gráficas para analizar la relación entre:

    - Número de simulaciones MCTS.
    - Porcentaje de victorias.
    - Tiempo promedio por jugada.
    """

    simulaciones = [
        r["simulaciones"]
        for r in resultados
    ]

    winrates = [
        r["porcentaje_victorias"]
        for r in resultados
    ]

    tiempos = [
        r["tiempo_promedio_jugada"]
        for r in resultados
    ]

    # --------------------------------------------------
    # GRÁFICA 1: PORCENTAJE DE VICTORIAS
    # --------------------------------------------------

    plt.figure(figsize=(8, 5))

    plt.plot(
        simulaciones,
        winrates,
        marker="o",
        linewidth=2
    )

    plt.xlabel("Número de simulaciones MCTS")
    plt.ylabel("Porcentaje de victorias (%)")

    plt.title(
        "Efectividad de MCTS según el número de simulaciones"
    )

    plt.ylim(0, 105)
    plt.grid(True, linestyle="--", alpha=0.5)

    # Mostrar el porcentaje encima de cada punto.
    for x, y in zip(simulaciones, winrates):
        plt.annotate(
            f"{y:.1f}%",
            (x, y),
            textcoords="offset points",
            xytext=(0, 8),
            ha="center"
        )

    plt.tight_layout()

    plt.savefig(
        "mcts_winrate.png",
        dpi=300
    )

    plt.show()

    # --------------------------------------------------
    # GRÁFICA 2: TIEMPO PROMEDIO POR JUGADA
    # --------------------------------------------------

    plt.figure(figsize=(8, 5))

    plt.plot(
        simulaciones,
        tiempos,
        marker="o",
        linewidth=2
    )

    plt.xlabel("Número de simulaciones MCTS")
    plt.ylabel("Tiempo promedio por jugada (segundos)")

    plt.title(
        "Costo computacional de MCTS"
    )

    plt.grid(True, linestyle="--", alpha=0.5)

    for x, y in zip(simulaciones, tiempos):
        plt.annotate(
            f"{y:.3f}s",
            (x, y),
            textcoords="offset points",
            xytext=(0, 8),
            ha="center"
        )

    plt.tight_layout()

    plt.savefig(
        "mcts_tiempo.png",
        dpi=300
    )

    plt.show()

        # Gráfica adicional: Movimientos promedio por partida
    movimientos = [r["movimientos_promedio"] for r in resultados]

    plt.figure(figsize=(8, 5))
    plt.plot(simulaciones, movimientos, marker="o", color="#2ca02c", linewidth=2)
    plt.xlabel("Número de simulaciones MCTS")
    plt.ylabel("Movimientos promedio por partida")
    plt.title("Eficiencia de juego: Duración de la partida según MCTS")
    plt.grid(True, linestyle="--", alpha=0.5)

    for x, y in zip(simulaciones, movimientos):
        plt.annotate(
            f"{y:.1f}",
            (x, y),
            textcoords="offset points",
            xytext=(0, 8),
            ha="center"
        )

    plt.tight_layout()
    plt.savefig("mcts_movimientos.png", dpi=300)
    plt.show()

        # Gráfica adicional: Trade-off Tiempo vs Winrate
    plt.figure(figsize=(8, 5))
    plt.scatter(tiempos, winrates, color="#d62728", s=100, zorder=5)
    plt.plot(tiempos, winrates, linestyle="--", color="gray", alpha=0.7)

    plt.xlabel("Tiempo promedio por jugada (segundos)")
    plt.ylabel("Porcentaje de victorias (%)")
    plt.title("Relación Costo-Beneficio (Trade-off Tiempo vs. Winrate)")
    plt.grid(True, linestyle="--", alpha=0.5)

    for x, y, sim in zip(tiempos, winrates, simulaciones):
        plt.annotate(
            f"{sim} sim ({y:.0f}%)",
            (x, y),
            textcoords="offset points",
            xytext=(0, 10),
            ha="center",
            fontweight="bold"
        )

    plt.tight_layout()
    plt.savefig("mcts_tradeoff.png", dpi=300)
    plt.show()