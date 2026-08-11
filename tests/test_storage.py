"""Tests de persistencia JSON, historial y rankings."""

from engine import NEGRO, BLANCO
from engine.scoring import Partida
from storage import store


def test_guardar_y_cargar_partida(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DIRECTORIO_PARTIDAS", tmp_path / "games")
    monkeypatch.setattr(store, "RUTA_HISTORIAL", tmp_path / "historial.json")

    partida = Partida(9)
    partida.jugar(3, 3)
    partida.jugar(4, 4)
    partida.jugar(3, 4)
    partida.pasar()
    partida.pasar()
    assert partida.terminada

    jugadores = {NEGRO: "humano", BLANCO: "mcts-800"}
    datos = store.guardar_partida(partida, jugadores, {"simulaciones": 800})

    cargada = store.cargar_partida(datos["id"])
    assert cargada["board_size"] == 9
    assert cargada["jugadores"]["B"] == "humano"
    assert cargada["jugadores"]["W"] == "mcts-800"
    assert cargada["resultado"]["ganador"] in (NEGRO, BLANCO)

    reconstruida = store.reconstruir_partida(cargada)
    assert reconstruida.resultado["ganador"] == partida.resultado["ganador"]
    assert reconstruida.tablero.celdas == partida.tablero.celdas


def test_historial_y_rankings(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DIRECTORIO_PARTIDAS", tmp_path / "games")
    monkeypatch.setattr(store, "RUTA_HISTORIAL", tmp_path / "historial.json")

    def partida_con_resultado(jugador_b, jugador_w, ganador):
        p = Partida(9)
        p.jugar(0, 0)
        p.pasar()
        p.pasar()
        store.guardar_partida(p, {NEGRO: jugador_b, BLANCO: jugador_w},
                              {"simulaciones": 250})
        # forzamos el ganador esperado re-escribiendo el resultado
        return p

    p1 = partida_con_resultado("mcts-250", "mcts-800", NEGRO)
    # garantizar que negro gana la primera (komi no alcanza a superar)
    assert p1.resultado["ganador"] == NEGRO

    p2 = partida_con_resultado("mcts-250", "aleatorio", NEGRO)

    rankings = store.calcular_rankings()
    por_nombre = {r["jugador"]: r for r in rankings["rankings"]}
    assert por_nombre["mcts-250"]["victorias"] == 2
    assert por_nombre["mcts-250"]["win_rate"] == 1.0
    assert por_nombre["mcts-800"]["derrotas"] == 1
    assert por_nombre["aleatorio"]["derrotas"] == 1


def test_listar_partidas(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DIRECTORIO_PARTIDAS", tmp_path / "games")
    monkeypatch.setattr(store, "RUTA_HISTORIAL", tmp_path / "historial.json")

    partida = Partida(9)
    partida.jugar(1, 1)
    store.guardar_partida(partida, {NEGRO: "humano", BLANCO: "humano"},
                          {"simulaciones": 0})

    lista = store.listar_partidas()
    assert len(lista) == 1
    assert lista[0]["num_movimientos"] == 1