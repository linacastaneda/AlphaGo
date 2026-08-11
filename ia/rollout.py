"""Playouts heurísticos para el MCTS baseline.

Las simulaciones priorizan capturas, evitan suicidios (ya filtrado por el
motor) y valoran puntos con más libertades, filtrando movimientos inútiles.
"""

import random

from motor import VACIO, oponer
from motor.scoring import calcular_puntaje


def _calcular_pesos(tablero, color):
    """Calcula un peso por cada movimiento legal según heurísticas ligeras.

    Un único barrido de grupos por posición (O(N²)) evita recalcular BFS por
    vecino. Devuelve una lista de ``(fila, col, peso)``.
    """
    color_oponente = oponer(color)
    grupos = tablero.grupos_con_libertades()
    movimientos = []
    tamano = tablero.tamano
    celdas = tablero.celdas

    for fila, col in tablero.celdas_vacias():
        if (fila, col) == tablero.punto_ko:
            continue
        vecinos_vacios = 0
        capturas_estimadas = 0

        if fila > 0:
            celda = celdas[fila - 1][col]
            if celda == VACIO:
                vecinos_vacios += 1
            elif celda == color_oponente:
                info = grupos.get((fila - 1, col))
                if info and info["libertades"] == 1:
                    capturas_estimadas += info["tamano"]
        if fila < tamano - 1:
            celda = celdas[fila + 1][col]
            if celda == VACIO:
                vecinos_vacios += 1
            elif celda == color_oponente:
                info = grupos.get((fila + 1, col))
                if info and info["libertades"] == 1:
                    capturas_estimadas += info["tamano"]
        if col > 0:
            celda = celdas[fila][col - 1]
            if celda == VACIO:
                vecinos_vacios += 1
            elif celda == color_oponente:
                info = grupos.get((fila, col - 1))
                if info and info["libertades"] == 1:
                    capturas_estimadas += info["tamano"]
        if col < tamano - 1:
            celda = celdas[fila][col + 1]
            if celda == VACIO:
                vecinos_vacios += 1
            elif celda == color_oponente:
                info = grupos.get((fila, col + 1))
                if info and info["libertades"] == 1:
                    capturas_estimadas += info["tamano"]

        if vecinos_vacios == 0 and capturas_estimadas == 0:
            # sin libertades directas ni capturas: puede ser conexión suicida o
            # extensión a un grupo con libertades; se valida legalidad completa
            if not tablero.es_movimiento_legal(fila, col, color):
                continue
            peso = 1.0
        else:
            peso = 1.0 + 8.0 * capturas_estimadas + 0.3 * vecinos_vacios

        movimientos.append((fila, col, peso))

    return movimientos


def _probabilidad_pase(tablero):
    """Probabilidad de pasar en el rollout según lo lleno que esté el tablero.

    Un tablero casi lleno se acerca al final de la partida: en Go es correcto
    pasar cuando ya no queda territorio útil. Sube progresivamente desde 0
    (tablero con >25% de casillas libres) hasta ~0.5 en tableros saturados.
    Así las simulaciones terminan por doble pase en lugar de rellenar a ciegas.
    """
    vacias = len(tablero.celdas_vacias())
    total = tablero.tamano * tablero.tamano
    fraccion_libre = vacias / total
    if fraccion_libre >= 0.25:
        return 0.0
    if fraccion_libre <= 0.02:
        return 0.5
    pendiente = (0.25 - fraccion_libre) / (0.25 - 0.02)
    return round(0.5 * pendiente, 3)


def elegir_movimiento_heurístico(tablero, color, aleatorio=False):
    """Elige un movimiento para el rollout: aleatorio con sesgo heurístico.

    Devuelve ``(fila, col)`` o ``None`` si no hay movimientos legales (pase)
    o si la partida está tan llena que pasar es lo natural.
    """
    if random.random() < _probabilidad_pase(tablero):
        return None
    movimientos = _calcular_pesos(tablero, color)
    if not movimientos:
        return None

    total = sum(peso for _, _, peso in movimientos)
    objetivo = random.uniform(0.0, total)
    acumulado = 0.0
    for fila, col, peso in movimientos:
        acumulado += peso
        if acumulado >= objetivo:
            return (fila, col)
    return (movimientos[-1][0], movimientos[-1][1])


def simular_partida(tablero_inicial, color_inicial, komi=7.5, pliegues_max=40):
    """Juega una partida aleatoria heurística desde el estado dado.

    Devuelve ``(ganador, tablero)`` tras el corte.
    """
    tablero = tablero_inicial.copiar()
    color = color_inicial
    pases = 0

    for _ in range(pliegues_max):
        if not tablero.celdas_vacias():
            break
        movimiento = elegir_movimiento_heurístico(tablero, color)
        if movimiento is None:
            pases += 1
            color = oponer(color)
            if pases >= 2:
                break
            continue
        pases = 0
        tablero.colocar_piedra(movimiento[0], movimiento[1], color)
        color = oponer(color)

    resultado = calcular_puntaje(tablero, komi)
    return resultado["ganador"], tablero