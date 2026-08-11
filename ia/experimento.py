"""Experimentos: enfrentamientos entre configuraciones de IA.

Permite comparar baseline vs baseline (Experimento 1: simulaciones),
baseline vs baseline+red (Experimento 2) o configuraciones arbitrarias.
"""

import random
import time

from motor import BLANCO, NEGRO, color_a_simbolo
from motor.scoring import Partida
from .mcts import MCTS, crear_mcts
from .rival_lina import RivalLina

LIMITE_MOVIMIENTOS_POR_DEFECTO = 360


def construir_ia(config: str, tiempo_limite_ms: int | None = None):
    """Devuelve una función ``(config) -> jugador`` que decide sobre una Partida.

    ``config`` acepta: ``aleatorio``, ``mcts-<sims>``, ``mcts-<sims>+red``
    o ``lina-<sims>`` (la MCTS de Lina, con handicap aplicado en su adaptador).
    """
    if config == "aleatorio":
        return lambda partida: _jugada_aleatoria(partida)

    if config.startswith("lina-"):
        simulaciones = int(config.split("-")[1])
        rival = RivalLina(simulaciones=simulaciones,
                          tiempo_limite_ms=tiempo_limite_ms)
        return lambda partida: rival.mejor_jugada(partida)

    con_red = config.endswith("+red")
    base = config.removesuffix("+red")
    if not base.startswith("mcts-"):
        raise ValueError(f"configuración desconocida: {config}")
    simulaciones = int(base.split("-")[1])

    if con_red:
        from .redes import cargar_redes
        redes = cargar_redes()
        if redes is None:
            raise ValueError("no hay modelos para config +red (falta models/policy.onnx)")
        mcts = MCTS(simulaciones=simulaciones,
                    tiempo_limite_ms=tiempo_limite_ms, redes=redes)
    else:
        mcts = crear_mcts(simulaciones=simulaciones,
                          tiempo_limite_ms=tiempo_limite_ms)
    return lambda partida: mcts.mejor_jugada(partida)


def _jugada_aleatoria(partida) -> dict:
    """Jugador de referencia: jugada legal al azar (o pase con poca probabilidad)."""
    tabla = partida.tablero
    movimientos = tabla.obtener_movimientos_legales(partida.turno)
    if not movimientos or random.random() < 0.05:
        return {"fila": None, "col": None, "pase": True}
    fila, col = random.choice(movimientos)
    return {"fila": fila, "col": col, "pase": False}


def _medir(jugada: dict, color: int) -> dict:
    return {"color": color, **jugada}


def jugar_partida(jugador_negro, jugador_blanco, komi: float = 7.5,
                  limite_movimientos: int = LIMITE_MOVIMIENTOS_POR_DEFECTO,
                  semilla: int | None = None,
                  tamano: int = 9,
                  registrar_metadatos: bool = True,
                  al_jugar=None) -> dict:
    """Juega una partida completa entre dos funciones decisión (IA o aleatorio).

    ``al_jugar(color, jugada, tiempo_ms)`` se invoca tras cada movimiento
    (permite registrar SGF u otros formatos sin tocar el motor).
    """
    if semilla is not None:
        random.seed(semilla)
    partida = Partida(tamano, komi)
    jugadores = {NEGRO: jugador_negro, BLANCO: jugador_blanco}
    tiempos = {NEGRO: [], BLANCO: []}
    num_movimientos = 0

    while not partida.terminada:
        if num_movimientos >= limite_movimientos:
            partida.finalizar()
            break
        color = partida.turno
        inicio = time.perf_counter()
        jugada = jugadores[color](partida)
        tiempos[color].append((time.perf_counter() - inicio) * 1000)

        if jugada.get("pase"):
            partida.pasar()
        else:
            partida.jugar(jugada["fila"], jugada["col"])
        if registrar_metadatos:
            partida.agregar_metadatos_ultimo_movimiento(
                {"tiempo_ms": round(tiempos[color][-1], 2)})
        num_movimientos += 1
        if al_jugar is not None:
            al_jugar(color, jugada, tiempos[color][-1])

    resultado = partida.resultado
    ganador = resultado.get("ganador") if resultado else None
    return {
        "ganador": ganador,
        "por_rendicion": bool(resultado and resultado.get("por_rendicion")),
        "num_movimientos": num_movimientos,
        "terminada": partida.terminada,
        "resultado": resultado,
        "tiempos_ms": {color_a_simbolo(c): tiempos[c] for c in (NEGRO, BLANCO)},
    }


def experimento(config_negro: str, config_blanco: str, partidas: int = 10,
                tiempo_limite_ms: int | None = None,
                semilla: int | None = None,
                limite_movimientos: int = LIMITE_MOVIMIENTOS_POR_DEFECTO,
                tamano: int = 9) -> dict:
    """Juega ``partidas`` enfrentamientos y agrega victorias, empates y tiempos."""
    jugador_negro = construir_ia(config_negro, tiempo_limite_ms)
    jugador_blanco = construir_ia(config_blanco, tiempo_limite_ms)

    victorias_negro = 0
    victorias_blanco = 0
    empates = 0
    tiempos = {config_negro: [], config_blanco: []}
    movimientos = []

    for i in range(partidas):
        resultado = jugar_partida(
            jugador_negro, jugador_blanco,
            semilla=semilla + i if semilla is not None else None,
            limite_movimientos=limite_movimientos,
            tamano=tamano)
        ganador = resultado["ganador"]
        if ganador is None:
            empates += 1
        elif ganador == NEGRO:
            victorias_negro += 1
        else:
            victorias_blanco += 1
        movimientos.append(resultado["num_movimientos"])
        for config, simbolo in ((config_negro, "B"), (config_blanco, "W")):
            tiempos[config].extend(resultado["tiempos_ms"].get(simbolo, []))

    def _promedio(lista):
        return round(sum(lista) / len(lista), 2) if lista else 0.0

    def _media_sims(config):
        if config.startswith("lina-"):
            return int(config.split("-")[1])
        base = config.removesuffix("+red")
        return int(base.split("-")[1]) if base.startswith("mcts-") else 0

    return {
        "negro": config_negro,
        "blanco": config_blanco,
        "partidas": partidas,
        "victorias_negro": victorias_negro,
        "victorias_blanco": victorias_blanco,
        "empates": empates,
        "win_rate_negro": round(victorias_negro / partidas, 3) if partidas else 0.0,
        "win_rate_blanco": round(victorias_blanco / partidas, 3) if partidas else 0.0,
        "movimientos_promedio": round(sum(movimientos) / len(movimientos), 1) if movimientos else 0.0,
        "tiempo_promedio_ms": {
            config_negro: _promedio(tiempos[config_negro]),
            config_blanco: _promedio(tiempos[config_blanco]),
        },
        "simulaciones": {
            config_negro: _media_sims(config_negro),
            config_blanco: _media_sims(config_blanco),
        },
    }