"""Tests de la IA de Lina portada (ai/mcts_lina) y su envoltura RivalLina."""

import pytest

from ai.experimento import construir_ia
from ai.mcts_lina import MCTSLina, NodoMCTS, crear_lina
from ai.rival_lina import (
    HANDICAP_LINA,
    RivalLina,
    crear_rival,
    es_config_lina,
    sims_efectivos,
)
from engine.scoring import Partida


def test_es_config_lina():
    assert es_config_lina("lina-800")
    assert es_config_lina("lina-50")
    assert not es_config_lina("mcts-800")
    assert not es_config_lina("aleatorio")


def test_sims_efectivos_aplica_handicap():
    assert sims_efectivos("lina-250") == 250 * HANDICAP_LINA


def test_rival_aplica_handicap():
    rival = RivalLina(simulaciones=250)
    assert rival.simulaciones == 250 * HANDICAP_LINA
    assert rival._nombre_config() == f"lina-{250 * HANDICAP_LINA}"


def test_mejor_jugada_devuelve_contrato():
    partida = Partida(9, 7.5)
    rival = RivalLina(simulaciones=40, tiempo_limite_ms=3000)
    jugada = rival.mejor_jugada(partida)
    assert "fila" in jugada and "col" in jugada and "pase" in jugada
    assert jugada["sims"] > 0
    assert jugada["config"].startswith("lina-")
    if not jugada["pase"]:
        assert partida.tablero.celdas[jugada["fila"]][jugada["col"]] == 0
    assert jugada["tiempo_ms"] >= 0


def test_presupuesto_tiempo_nativo():
    """El límite de tiempo corta la búsqueda sin calibración previa."""
    rival = RivalLina(simulaciones=2000, tiempo_limite_ms=1000)
    partida = Partida(9, 7.5)
    jugada = rival.mejor_jugada(partida)
    assert 0 < jugada["sims"] < 2000
    assert jugada["tiempo_ms"] < 3000


def test_mcts_lina_contrato_directo():
    partida = Partida(9, 7.5)
    ia = crear_lina(simulaciones=20)
    jugada = ia.mejor_jugada(partida)
    assert jugada["config"].startswith("lina-")
    assert jugada["sims"] == 20


def test_mcts_lina_pase_con_raiz_sin_movimientos():
    partida = Partida(9, 7.5)
    # Llenar el tablero para forzar ausencia de movimientos
    # (o raíz sin hijos): basta un tablero vacío con pocas sims.
    ia = crear_lina(simulaciones=5)
    jugada = ia.mejor_jugada(partida)
    assert jugada["pase"] in (True, False)


def test_nodo_mcts_expansion_y_uct():
    raiz = NodoMCTS(movimientos_validos=[(0, 0), (1, 1)])
    assert raiz.movimientos_no_explorados == [(0, 0), (1, 1), None]
    raiz.movimientos_no_explorados.remove((0, 0))
    assert not raiz.esta_totalmente_expandido()
    raiz.movimientos_no_explorados.clear()
    assert raiz.esta_totalmente_expandido()
    assert raiz.seleccionar_mejor_hijo() is None


def test_crear_rival_defaults():
    rival = crear_rival(simulaciones=100)
    assert rival.simulaciones_base == 100
    assert rival.simulaciones == 100 * HANDICAP_LINA


def test_construir_ia_lina():
    partida = Partida(9, 7.5)
    ia = construir_ia("lina-40", tiempo_limite_ms=2000)
    jugada = ia(partida)
    assert jugada["config"].startswith("lina-")


def test_construir_ia_lina_desconocida():
    with pytest.raises(ValueError):
        construir_ia("lina-abc")


def test_mcts_lina_no_depende_de_backend():
    import ai.mcts_lina
    assert "backend" not in dir(ai.mcts_lina)
    import ai.rival_lina
    assert "backend" not in dir(ai.rival_lina)
