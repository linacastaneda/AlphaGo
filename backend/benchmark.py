"""
Benchmark para evaluar el desempeño de la IA de Go.

Se compara una IA basada en MCTS contra un jugador aleatorio
utilizando diferentes cantidades de simulaciones.
"""

import random
import time
from graficas import graficar_resultados_benchmark
from motor_go import JuegoGo, NEGRA, BLANCA
from ia_go import InteligenciaGo


def movimiento_aleatorio(juego):
    """
    Selecciona una jugada aleatoria válida.
    Si no existen movimientos legales, pasa el turno.
    """
    movimientos = juego.obtener_movimientos_validos()
    if not movimientos:
        return None
    return random.choice(movimientos)


def jugar_partida(simulaciones=50, tamano=5, ia_color=NEGRA):
    """
    Juega una partida completa entre la IA MCTS y un jugador aleatorio.
    """
    juego = JuegoGo(tamano=tamano)
    ia = InteligenciaGo(simulaciones=simulaciones)

    tiempos_ia = []
    movimientos_totales = 0
    limite_movimientos = tamano * tamano * 3

    while (
        not juego.partida_terminada()
        and movimientos_totales < limite_movimientos
    ):
        es_turno_ia = (juego.jugador_actual == ia_color)

        if es_turno_ia:
            inicio = time.perf_counter()
            movimiento = ia.seleccionar_movimiento(juego)
            fin = time.perf_counter()
            tiempos_ia.append(fin - inicio)
        else:
            movimiento = movimiento_aleatorio(juego)

        # Aplicación de la jugada
        if movimiento is None:
            juego.pasar_turno()
        else:
            exito = juego.jugar(movimiento[0], movimiento[1])
            # Si el motor rechazó la jugada, pasa turno como salvaguarda
            if not exito:
                juego.pasar_turno()

        movimientos_totales += 1

    # Evaluación final
    puntos_negras, puntos_blancas = juego.calcular_puntuacion()

    if puntos_negras > puntos_blancas:
        ganador = NEGRA
    elif puntos_blancas > puntos_negras:
        ganador = BLANCA
    else:
        ganador = 0

    return ganador, tiempos_ia, movimientos_totales


def ejecutar_benchmark(simulaciones, partidas=10, tamano=5):
    """
    Ejecuta varias partidas para una determinada cantidad de simulaciones.
    """
    victorias = 0
    derrotas = 0
    empates = 0

    todos_los_tiempos_ia = []
    duraciones = []

    for numero in range(partidas):
        ia_color = NEGRA if numero % 2 == 0 else BLANCA

        ganador, tiempos_partida, movimientos = jugar_partida(
            simulaciones=simulaciones,
            tamano=tamano,
            ia_color=ia_color
        )

        if ganador == ia_color:
            victorias += 1
            resultado = "Victoria"
        elif ganador == 0:
            empates += 1
            resultado = "Empate"
        else:
            derrotas += 1
            resultado = "Derrota"

        todos_los_tiempos_ia.extend(tiempos_partida)
        duraciones.append(movimientos)

        tiempo_prom_partida = (
            sum(tiempos_partida) / len(tiempos_partida)
            if tiempos_partida else 0.0
        )

        print(
            f"Partida {numero + 1:02d}: "
            f"{resultado:<8} | "
            f"IA={'Negra ' if ia_color == NEGRA else 'Blanca'} | "
            f"Movimientos={movimientos:<3} | "
            f"Tiempo prom. IA={tiempo_prom_partida:.4f}s"
        )

    porcentaje_victorias = (victorias / partidas) * 100
    
    tiempo_promedio_global = (
        sum(todos_los_tiempos_ia) / len(todos_los_tiempos_ia)
        if todos_los_tiempos_ia else 0.0
    )
    
    movimientos_promedio = sum(duraciones) / len(duraciones)

    return {
        "simulaciones": simulaciones,
        "partidas": partidas,
        "victorias": victorias,
        "derrotas": derrotas,
        "empates": empates,
        "porcentaje_victorias": porcentaje_victorias,
        "tiempo_promedio_jugada": tiempo_promedio_global,
        "movimientos_promedio": movimientos_promedio
    }


def mostrar_resultados(resultados):
    """Muestra una tabla resumen en consola."""
    print("\n" + "=" * 90)
    print("RESULTADOS DEL BENCHMARK")
    print("=" * 90)

    encabezado = (
        f"{'Simulaciones':<15}"
        f"{'Victorias':<12}"
        f"{'Derrotas':<12}"
        f"{'Empates':<10}"
        f"{'% Victoria':<15}"
        f"{'Tiempo/jugada':<18}"
        f"{'Mov. promedio':<15}"
    )

    print(encabezado)
    print("-" * 90)

    for r in resultados:
        print(
            f"{r['simulaciones']:<15}"
            f"{r['victorias']:<12}"
            f"{r['derrotas']:<12}"
            f"{r['empates']:<10}"
            f"{r['porcentaje_victorias']:<15.1f}"
            f"{r['tiempo_promedio_jugada']:<18.4f}"
            f"{r['movimientos_promedio']:<15.1f}"
        )

    print("=" * 90)


if __name__ == "__main__":
    TAMANO = 5
    PARTIDAS = 10
    configuraciones = [10, 25, 50, 100]

    resultados = []

    for simulaciones in configuraciones:
        print(f"\nEvaluando MCTS con {simulaciones} simulaciones...")
        resultado = ejecutar_benchmark(
            simulaciones=simulaciones,
            partidas=PARTIDAS,
            tamano=TAMANO
        )
        resultados.append(resultado)

    mostrar_resultados(resultados)
      # Generamos las gráficas utilizando
    # los resultados REALES obtenidos.
    graficar_resultados_benchmark(resultados)