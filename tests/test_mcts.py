"""Tests del MCTS: selección, expansión, retropropagación y resultados."""

from engine import NEGRO, BLANCO
from engine.scoring import Partida
from ai.mcts import MCTS, Nodo, CLAVE_PASE


def test_mejor_jugada_devuelve_estructura():
    p = Partida(9)
    mcts = MCTS(simulaciones=30)
    resultado = mcts.mejor_jugada(p)
    assert set(resultado) >= {"fila", "col", "pase", "win_rate", "sims", "nodes", "tiempo_ms"}
    assert resultado["sims"] <= 30
    if not resultado["pase"]:
        assert 0 <= resultado["fila"] < 9
        assert 0 <= resultado["col"] < 9


def test_mejor_jugada_no_devuelve_movimiento_ilegal():
    p = Partida(9)
    p.jugar(4, 4)
    mcts = MCTS(simulaciones=20)
    resultado = mcts.mejor_jugada(p)
    if not resultado["pase"]:
        assert p.tablero.es_movimiento_legal(resultado["fila"], resultado["col"], BLANCO)


def test_expansion_crea_hijos():
    p = Partida(9)
    tablero = p.tablero.copiar()
    raiz = Nodo()
    mcts = MCTS(simulaciones=1)
    creados = mcts._expandir(raiz, tablero, NEGRO)
    # 81 puntos libres + pase
    assert creados == 82
    assert CLAVE_PASE in raiz.hijos


def test_retropropagacion_alterna_valor():
    p = Partida(9)
    mcts = MCTS(simulaciones=1)
    raiz = Nodo(padre=None)
    hijo = Nodo(fila=1, col=1, padre=raiz)
    raiz.hijos[(1, 1)] = hijo
    raiz.hijos[CLAVE_PASE] = Nodo(padre=raiz)
    camino = [raiz, hijo]
    mcts._retropropagar(camino, 1.0)
    assert hijo.visitas == 1
    assert hijo.q == 1.0
    assert raiz.visitas == 1
    assert raiz.q == 0.0


def test_mejor_jugada_juega_alternando():
    """Si negro ya jugó, la IA responde como blanco con una jugada legal."""
    p = Partida(9)
    p.jugar(3, 3)
    mcts = MCTS(simulaciones=25)
    resultado = mcts.mejor_jugada(p)
    if not resultado["pase"]:
        # blanco juega ahora
        p.jugar(resultado["fila"], resultado["col"])
        assert p.turno == NEGRO


def test_config_ia():
    mcts = MCTS(simulaciones=800)
    assert mcts.simulaciones == 800
    assert mcts.exploracion == 1.4


def test_analizar_devuelve_top_opciones():
    p = Partida(9)
    p.jugar(4, 4)
    mcts = MCTS(simulaciones=40)
    analisis = mcts.analizar(p, n=5)
    assert set(analisis) >= {"opciones", "sims", "nodes", "tiempo_ms", "config"}
    assert 1 <= len(analisis["opciones"]) <= 5
    visitas = [o["visitas"] for o in analisis["opciones"]]
    assert visitas == sorted(visitas, reverse=True)
    for opcion in analisis["opciones"]:
        assert set(opcion) >= {"fila", "col", "pase", "visitas", "q", "win_rate"}
        if not opcion["pase"]:
            assert p.tablero.es_movimiento_legal(
                opcion["fila"], opcion["col"], BLANCO)
        else:
            assert opcion["fila"] is None and opcion["col"] is None