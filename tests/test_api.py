"""Tests de los endpoints principales de la API."""

import time

import pytest

from app import crear_app, PARTIDAS


@pytest.fixture()
def cliente(tmp_path, monkeypatch):
    from storage import store as modulo_store
    monkeypatch.setattr(modulo_store, "DIRECTORIO_PARTIDAS", tmp_path / "games")
    monkeypatch.setattr(modulo_store, "RUTA_HISTORIAL", tmp_path / "historial.json")
    PARTIDAS.clear()
    app = crear_app(prueba=True)
    return app.test_client()


def test_nueva_partida_pvp(cliente):
    respuesta = cliente.post("/api/game/new", json={"modo": "pvp"})
    datos = respuesta.get_json()
    assert respuesta.status_code == 200
    assert datos["modo"] == "pvp"
    assert datos["turno"] == 1
    assert datos["jugadores"]["B"] == "humano"


def test_jugar_movimiento(cliente):
    partida = cliente.post("/api/game/new", json={"modo": "pvp"}).get_json()
    identificador = partida["id"]
    respuesta = cliente.post(f"/api/game/{identificador}/move", json={"fila": 4, "col": 4})
    datos = respuesta.get_json()
    assert respuesta.status_code == 200
    assert datos["estado"]["turno"] == 2
    assert datos["estado"]["num_movimientos"] == 1


def test_movimiento_ilegal_rechazado(cliente):
    partida = cliente.post("/api/game/new", json={"modo": "pvp"}).get_json()
    identificador = partida["id"]
    cliente.post(f"/api/game/{identificador}/move", json={"fila": 4, "col": 4})
    respuesta = cliente.post(f"/api/game/{identificador}/move", json={"fila": 4, "col": 4})
    assert respuesta.status_code == 400


def test_pase_doble_finaliza_y_guarda(cliente):
    partida = cliente.post("/api/game/new", json={"modo": "pvp"}).get_json()
    identificador = partida["id"]
    cliente.post(f"/api/game/{identificador}/move", json={"fila": 4, "col": 4})
    cliente.post(f"/api/game/{identificador}/pass")
    respuesta = cliente.post(f"/api/game/{identificador}/pass")
    assert respuesta.get_json()["estado"]["terminada"] is True
    assert respuesta.get_json()["estado"]["resultado"]["ganador"] in (1, 2)
    # la partida quedó guardada en disco
    guardada = cliente.get(f"/api/game/{identificador}")
    assert guardada.status_code == 200


def test_rendicion(cliente):
    partida = cliente.post("/api/game/new", json={"modo": "pvp"}).get_json()
    identificador = partida["id"]
    respuesta = cliente.post(f"/api/game/{identificador}/resign", json={"color": "B"})
    datos = respuesta.get_json()
    assert datos["terminada"] is True
    assert datos["resultado"]["ganador"] == 2


def test_movimiento_ia(cliente):
    partida = cliente.post(
        "/api/game/new", json={"modo": "vs_ia", "simulaciones": "250"}).get_json()
    identificador = partida["id"]
    respuesta = cliente.post(f"/api/game/{identificador}/ai-move")
    datos = respuesta.get_json()
    assert respuesta.status_code == 200
    estado = datos["estado"]
    if not estado["terminada"]:
        ultimo = estado["movimientos"][-1]
        assert ultimo["ai"] is not None
        assert ultimo["ai"]["sims"] > 0
        assert ultimo["ai"]["config"].startswith("mcts-")


def test_metricas_y_perf(cliente):
    partida = cliente.post("/api/game/new", json={"modo": "pvp"}).get_json()
    cliente.post(f"/api/game/{partida['id']}/move", json={"fila": 0, "col": 0})
    metricas = cliente.get("/api/metrics").get_json()
    assert "rankings" in metricas
    assert "estadisticas_ia" in metricas
    perf_data = cliente.get("/api/perf").get_json()
    assert "endpoints" in perf_data
    assert "/api/metrics" in perf_data["endpoints"]


def test_partida_no_existente(cliente):
    respuesta = cliente.get("/api/game/noexiste")
    assert respuesta.status_code == 404


def test_ia_ia_juega_automatica(cliente):
    """En modo ia_ia la IA debe poder jugar ambos lados."""
    partida = cliente.post("/api/game/new", json={"modo": "ia_ia", "simulaciones": "250"}).get_json()
    identificador = partida["id"]
    for _ in range(3):
        cliente.post(f"/api/game/{identificador}/ai-move")
    estado = cliente.get(f"/api/game/{identificador}").get_json()
    assert estado["num_movimientos"] >= 2


def test_analisis_posicion_sin_modificar_partida(cliente):
    partida = cliente.post(
        "/api/game/new", json={"modo": "pvp", "simulaciones": "250"}).get_json()
    identificador = partida["id"]
    cliente.post(f"/api/game/{identificador}/move", json={"fila": 4, "col": 4})

    antes = cliente.get(f"/api/game/{identificador}").get_json()
    respuesta = cliente.post(f"/api/game/{identificador}/analysis",
                             json={"simulaciones": 40, "top": 3})
    datos = respuesta.get_json()
    despues = cliente.get(f"/api/game/{identificador}").get_json()

    assert respuesta.status_code == 200
    assert datos["turno"] == ("B" if antes["turno"] == 1 else "W")
    analisis = datos["analisis"]
    assert analisis["config"].startswith("mcts-")
    assert 1 <= len(analisis["opciones"]) <= 3
    visitas = [o["visitas"] for o in analisis["opciones"]]
    assert visitas == sorted(visitas, reverse=True)
    # el análisis no debe consumir turno ni modificar la partida
    assert despues["num_movimientos"] == antes["num_movimientos"]
    assert despues["turno"] == antes["turno"]


def test_experimento_ia(cliente):
    respuesta = cliente.post("/api/ai/experiment",
                             json={"negro": "aleatorio", "blanco": "aleatorio",
                                   "partidas": 2})
    datos = respuesta.get_json()
    assert respuesta.status_code == 200
    assert datos["partidas"] == 2
    assert datos["victorias_negro"] + datos["victorias_blanco"] + datos["empates"] == 2
    assert "tiempo_promedio_ms" in datos
    metricas = cliente.get("/api/metrics").get_json()
    assert metricas["experimentos"] and metricas["experimentos"][0]["partidas"] == 2