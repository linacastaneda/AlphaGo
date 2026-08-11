"""Tests de los endpoints principales de la API."""

import time

import pytest

from app import crear_app, PARTIDAS


@pytest.fixture()
def cliente(tmp_path, monkeypatch):
    from almacenamiento import store as modulo_store
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


def test_ia_ia_forzada_por_limite_de_movimientos(cliente):
    """Si las IA se estancan, el límite de movimientos cierra la partida."""
    partida = cliente.post("/api/game/new", json={
        "modo": "ia_ia", "simulaciones": "80",
        "tiempo_limite_ms": 250, "limite_movimientos": 6,
    }).get_json()
    identificador = partida["id"]
    assert partida["config"]["limite_movimientos"] == 6
    estado = partida
    for _ in range(20):
        respuesta = cliente.post(f"/api/game/{identificador}/ai-move").get_json()
        estado = respuesta["estado"]
        if estado["terminada"]:
            break
    assert estado["terminada"] is True
    assert estado["num_movimientos"] == 6


def test_vs_ia_finaliza_por_saturacion_sin_doble_pase(cliente):
    """Humanos vs IA no deben quedar colgadas: al llenarse el tablero el
    servidor cierra la partida aunque el humano nunca pase dos veces."""
    from app import PARTIDAS
    from motor import NEGRO, BLANCO
    partida = cliente.post("/api/game/new", json={
        "modo": "vs_ia", "simulaciones": "80", "tiempo_limite_ms": 200,
    }).get_json()
    identificador = partida["id"]
    sesion = PARTIDAS[identificador]
    # 9x9 = 81 celdas; el umbral de saturación (85%) son ~69 celdas.
    # Rellena el tablero directamente en el motor (posiciones sin capturar)
    # hasta superar el 85%, luego un movimiento humano dispara _forzar_limite.
    tamano = 9
    for fila in range(tamano):
        for col in range(tamano):
            # pinta el tablero casi lleno: el saturar es lo que debe cerrar
            sesion.partida.tablero.celdas[fila][col] = (
                NEGRO if col < tamano - 1 else BLANCO)
    # deja una sola celda vacía para que el human moverse sea legal (~98%)
    sesion.partida.tablero.celdas[0][tamano - 1] = 0
    ocupadas = sum(1 for f in sesion.partida.tablero.celdas for c in f if c != 0)
    assert ocupadas / (tamano * tamano) >= 0.85

    # un movimiento humano en turno negro dispara el cierre por saturación
    respuesta = cliente.post(f"/api/game/{identificador}/move",
                             json={"fila": 0, "col": tamano - 1})
    estado = respuesta.get_json()["estado"]
    assert estado["terminada"] is True
    assert estado["resultado"]["ganador"] in (1, 2)


def test_duelo_crea_jugadores_por_lado(cliente):
    partida = cliente.post("/api/game/new", json={
        "modo": "duelo", "simulaciones": "250",
        "jugador_negro": "mcts-250", "jugador_blanco": "mcts-l-250",
    }).get_json()
    assert partida["modo"] == "duelo"
    assert partida["jugadores"]["B"] == "mcts-250"
    assert partida["jugadores"]["W"] == "mcts-l-250"


def test_duelo_jugador_invalido_rechazado(cliente):
    respuesta = cliente.post("/api/game/new", json={
        "modo": "duelo", "simulaciones": "250",
        "jugador_negro": "kata-800", "jugador_blanco": "mcts-250",
    })
    assert respuesta.status_code == 400


def test_duelo_despacha_motor_por_color(cliente):
    partida = cliente.post("/api/game/new", json={
        "modo": "duelo", "simulaciones": "250",
        "jugador_negro": "mcts-250", "jugador_blanco": "mcts-l-250",
        "tiempo_limite_ms": 2000,
    }).get_json()
    identificador = partida["id"]

    cliente.post(f"/api/game/{identificador}/ai-move")
    negro = cliente.get(f"/api/game/{identificador}").get_json()
    assert negro["movimientos"][-1]["ai"]["config"].startswith("mcts-")

    cliente.post(f"/api/game/{identificador}/ai-move")
    blanco = cliente.get(f"/api/game/{identificador}").get_json()
    assert blanco["movimientos"][-1]["ai"]["config"].startswith("mcts-l-")


def test_duelo_humano_en_cualquier_lado(cliente):
    partida = cliente.post("/api/game/new", json={
        "modo": "duelo", "simulaciones": "250",
        "jugador_negro": "mcts-l-250", "jugador_blanco": "humano",
        "tiempo_limite_ms": 2000,
    }).get_json()
    identificador = partida["id"]
    # negro es IA (Lina), blanco es humano
    respuesta = cliente.post(f"/api/game/{identificador}/ai-move")
    datos = respuesta.get_json()
    assert datos["estado"]["movimientos"][-1]["ai"]["config"].startswith("mcts-l-")
    assert datos["estado"]["turno"] == 2


def test_torneo_valida_configs(cliente):
    respuesta = cliente.post("/api/ai/torneo", json={"configs": ["mara-800"]})
    assert respuesta.status_code == 400


def test_torneo_paralelo_devuelve_resumen(cliente):
    respuesta = cliente.post("/api/ai/torneo", json={
        "configs": ["mcts-100", "mcts-200"],
        "partidas": 2, "tamano": 7, "tiempo_limite_ms": 200,
    })
    assert respuesta.status_code == 200
    datos = respuesta.get_json()
    assert "resumen" in datos
    assert len(datos["resumen"]) == 2
    nombres = {f["config"] for f in datos["resumen"]}
    assert nombres == {"mcts-100", "mcts-200"}
    for fila in datos["resumen"]:
        total = fila["victorias"] + fila["derrotas"] + fila["empates"]
        assert total > 0
        assert "win_rate" in fila
        assert "tiempo_promedio_ms" in fila


def test_torneo_persiste_partidas_en_historial(cliente):
    """Las partidas del torneo deben guardarse y aparecer en el historial."""
    from almacenamiento import store
    respuesta = cliente.post("/api/ai/torneo", json={
        "configs": ["mcts-100", "mcts-l-100"],
        "partidas": 1, "tamano": 7, "tiempo_limite_ms": 150,
    })
    assert respuesta.status_code == 200
    guardadas = [p for p in store.listar_partidas()
                 if p["jugadores"].get("B") in ("mcts-100", "mcts-l-100")]
    assert len(guardadas) >= 1
    detalle = store.cargar_partida(guardadas[0]["id"])
    assert detalle["board_size"] == 7
    assert len(detalle["movimientos"]) > 0


def test_experimento_con_lina(cliente):
    respuesta = cliente.post("/api/ai/experiment",
                             json={"negro": "aleatorio", "blanco": "mcts-l-30",
                                   "partidas": 1, "tiempo_limite_ms": 1000,
                                   "limite_movimientos": 12})
    datos = respuesta.get_json()
    assert respuesta.status_code == 200
    assert datos["blanco"] == "mcts-l-30"
    assert datos["simulaciones"]["mcts-l-30"] == 30
    assert datos["tiempo_promedio_ms"]["mcts-l-30"] > 0



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


def test_flujo_replay_lista_y_carga(cliente):
    """El replay consume /api/games y /api/game/<id>: verifica su formato."""
    partida = cliente.post("/api/game/new", json={"modo": "pvp"}).get_json()
    identificador = partida["id"]
    cliente.post(f"/api/game/{identificador}/move", json={"fila": 4, "col": 4})
    cliente.post(f"/api/game/{identificador}/pass")
    cliente.post(f"/api/game/{identificador}/pass")

    lista = cliente.get("/api/games").get_json()["partidas"]
    resumen = next((p for p in lista if p["id"] == identificador), None)
    assert resumen is not None
    assert resumen["tablero"] == 9
    assert resumen["num_movimientos"] >= 2
    assert resumen["jugadores"]["B"] == "humano"
    assert resumen["ganador"] in ("B", "W")

    detalle = cliente.get(f"/api/game/{identificador}").get_json()
    assert detalle["id"] == identificador
    assert detalle["board_size"] == 9
    assert detalle["jugadores"]["B"] == "humano"
    for mov in detalle["movimientos"]:
        # el replay.js espera color como símbolo y coord como [fila, col]
        assert mov["color"] in ("B", "W")
        assert mov["player"] == mov["color"]


def test_replay_partida_en_curso_devuelve_coordenadas(cliente):
    """Una partida activa (sin guardar) también debe ser cargable por el replay."""
    partida = cliente.post("/api/game/new", json={"modo": "vs_ia"}).get_json()
    identificador = partida["id"]
    cliente.post(f"/api/game/{identificador}/move", json={"fila": 4, "col": 4})

    detalle = cliente.get(f"/api/game/{identificador}").get_json()
    assert detalle["id"] == identificador
    ultimo = detalle["movimientos"][-1]
    # en sesión viva el color puede venir como entero; coord siempre [fila, col]
    assert isinstance(ultimo["coord"], list) and len(ultimo["coord"]) == 2
    assert ultimo["color"] in (1, 2, "B", "W")