"""Tests del harness de experimentos comparativos de IA."""

import pytest

from ia.experimento import construir_ia, experimento, jugar_partida
from ia.mcts import crear_mcts
from motor import BLANCO, NEGRO


def test_jugar_partida_completa_entre_aleatorios():
    resultado = jugar_partida(
        construir_ia("aleatorio"),
        construir_ia("aleatorio"),
        semilla=42)
    assert resultado["terminada"] is True
    assert resultado["num_movimientos"] > 0
    assert resultado["ganador"] in (1, 2, None)
    assert set(resultado["tiempos_ms"]) == {"B", "W"}


def test_construir_ia_aleatorio():
    from motor.scoring import Partida
    p = Partida(9)
    jugada = construir_ia("aleatorio")(p)
    assert set(jugada) >= {"fila", "col", "pase"}
    if not jugada["pase"]:
        assert p.tablero.es_movimiento_legal(jugada["fila"], jugada["col"], NEGRO)


def test_construir_ia_config_invalida():
    with pytest.raises(ValueError):
        construir_ia("maquina-mara")


def test_experimento_agrega_totales():
    datos = experimento("aleatorio", "aleatorio", partidas=2, semilla=7)
    assert datos["partidas"] == 2
    assert datos["victorias_negro"] + datos["victorias_blanco"] + datos["empates"] == 2
    assert datos["win_rate_negro"] + datos["win_rate_blanco"] <= 1.0
    assert "tiempo_promedio_ms" in datos
    assert "movimientos_promedio" in datos


def test_experimento_mcts_igual_que_mejor_jugada():
    """El jugador construido debe delegar en mejor_jugada (config coherente)."""
    from motor.scoring import Partida
    p = Partida(9)
    mcts = crear_mcts(simulaciones=25)
    esperado = mcts.mejor_jugada(p)
    jugador = construir_ia("mcts-25")
    obtenido = jugador(p)
    assert set(obtenido) >= {"fila", "col", "pase", "win_rate"}
    assert obtenido["pase"] == esperado["pase"]


def test_bots_terminan_por_doble_pase_sin_llenar_tablero():
    """Dos IA enroscadas deben cerrar la partida por doble pase,
    no rellenar el tablero hasta el límite de movimientos."""
    resultado = jugar_partida(
        construir_ia("mcts-60", tiempo_limite_ms=400),
        construir_ia("mcts-60", tiempo_limite_ms=400),
        semilla=3, limite_movimientos=120)
    assert resultado["terminada"] is True
    assert resultado["num_movimientos"] < 120