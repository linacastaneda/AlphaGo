"""Tests de las redes policy/value y su integración como guía del MCTS."""

import numpy as np

from ai.mcts import MCTS, CLAVE_PASE
from ai.redes import RedesGo, cargar_redes, codificar
from engine import BLANCO, NEGRO
from engine.scoring import Partida


def _red_falsa(politica=None, valor=0.55):
    """Crea una RedesGo con f,_callables grabables (no requiere onnxruntime)."""
    llamadas_politica = {"n": 0}
    llamadas_valor = {"n": 0}

    def f_politica(X):
        llamadas_politica["n"] += 1
        if politica is not None:
            return politica(X)
        logits = np.zeros((1, 82), dtype=np.float32)
        return logits

    def f_valor(X):
        llamadas_valor["n"] += 1
        return np.array([[valor]], dtype=np.float32)

    return (RedesGo(9, f_politica, f_valor),
            llamadas_politica, llamadas_valor)


def test_codificar_devuelve_cinco_canales():
    import numpy as np
    p = Partida(9)
    p.jugar(4, 4)
    X = codificar(p.tablero, NEGRO)
    assert isinstance(X, np.ndarray)
    assert X.shape == (5, 9, 9)
    # la piedra negra está en el canal "propias" de negro
    assert X[0, 4, 4] == 1.0
    assert X[1, 4, 4] == 0.0
    # canal constante de normalización
    assert (X[4] == 1.0).all()


def test_cargar_redes_sin_modelos_devuelve_none(tmp_path):
    assert cargar_redes(tmp_path) is None


def test_distribucion_politica_incluye_pase_y_legales():
    p = Partida(9)
    p.jugar(4, 4)
    redes, _, _ = _red_falsa()
    movimientos, probs = redes.distribucion_politica(p.tablero, BLANCO)
    assert set(probs) >= {CLAVE_PASE}
    for fila, col in movimientos:
        assert (fila, col) in probs
    total = sum(probs.values())
    assert 0.9999 < total <= 1.0001


def test_estimar_valor_clamp():
    p = Partida(9)
    redes, _, _ = _red_falsa(valor=0.0)
    assert redes.estimar_valor(p.tablero, NEGRO) == 0.0


def test_mcts_con_red_usa_politica_y_valor():
    p = Partida(9)
    redes, n_pol, n_val = _red_falsa()
    mcts = MCTS(simulaciones=40, redes=redes)
    resultado = mcts.mejor_jugada(p)
    assert resultado["config"] == "mcts-40+red"
    assert n_pol["n"] > 0
    assert n_val["n"] > 0
    analisis = mcts.analizar(p, n=3)
    assert analisis["config"].endswith("+red")
    assert 1 <= len(analisis["opciones"]) <= 3
    for opcion in analisis["opciones"]:
        assert "visitas" in opcion


def test_mcts_sin_red_mantiene_baseline():
    p = Partida(9)
    mcts = MCTS(simulaciones=40)
    resultado = mcts.mejor_jugada(p)
    assert resultado["config"] == "mcts-40"
    assert "win_rate" in resultado