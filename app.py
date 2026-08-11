"""Aplicación web de Go inspirada en AlphaGo.

Servidor Flask con API REST, MCTS baseline y middleware de instrumentación.
"""

import resource
import time
from threading import Lock

from flask import Flask, g, jsonify, request, send_from_directory

from ai.mcts import crear_mcts
from ai.rival_lina import es_config_lina
from engine import NEGRO, BLANCO, color_a_simbolo, simbolo_a_color
from engine.scoring import Partida
from storage import perf, store

RUTA_BASE = store.RUTA_BASE
MODOS = {"pvp", "vs_ia", "ia_ia", "duelo"}
PRESETS_SIMULACIONES = {"250": 250, "800": 800, "2000": 2000}

PARTIDAS = {}
_CANDADO = Lock()

_contador_memoria = {"n": 0}


class SesionPartida:
    """Estado en memoria de una partida activa."""

    def __init__(self, identificador, partida, jugadores, modo, config):
        self.id = identificador
        self.partida = partida
        self.jugadores = jugadores
        self.modo = modo
        self.config = config
        self.ultimo_evento = time.time()

    def es_ia(self, color: int) -> bool:
        return str(self.jugadores.get(color, "")).startswith(
            ("mcts", "alphago", "ia", "lina"))

    def turno_actual(self):
        return self.partida.turno

    def marcar_evento(self):
        self.ultimo_evento = time.time()

    def medir_tiempo_jugador(self) -> float:
        ahora = time.time()
        delta = (ahora - self.ultimo_evento) * 1000
        self.ultimo_evento = ahora
        return round(delta, 2)


def crear_app(prueba: bool = False) -> Flask:
    app = Flask(__name__, static_folder="static", static_url_path="/")
    if prueba:
        app.config["TESTING"] = True

    @app.before_request
    def _inicio_cronometro():
        g._inicio = time.perf_counter()

    @app.after_request
    def _medir_latencia(respuesta):
        tiempo = (time.perf_counter() - g._inicio) * 1000
        perf.registrar_latencia_endpoint(request.path, tiempo, respuesta.status_code)
        global _contador_memoria
        _contador_memoria["n"] += 1
        if _contador_memoria["n"] % 25 == 0:
            rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            perf.registrar_memoria(rss)
        return respuesta

    @app.errorhandler(ValueError)
    def _error_validacion(error):
        return jsonify({"error": str(error)}), 400

    @app.errorhandler(FileNotFoundError)
    def _error_no_encontrado(error):
        return jsonify({"error": str(error)}), 404

    @app.get("/")
    def _indice():
        return send_from_directory(app.static_folder, "index.html")

    @app.post("/api/game/new")
    def _nueva_partida():
        cuerpo = request.get_json(silent=True) or {}
        modo = cuerpo.get("modo", "vs_ia")
        if modo not in MODOS:
            return jsonify({"error": "modo inválido"}), 400
        tamano = int(cuerpo.get("tamano", 9))
        if tamano not in (9, 13, 19):
            return jsonify({"error": "tamano debe ser 9, 13 o 19"}), 400
        komi = float(cuerpo.get("komi", 7.5))

        simulaciones = PRESETS_SIMULACIONES.get(str(cuerpo.get("simulaciones", "800")), 800)
        jugador_negro = cuerpo.get("jugador_negro") or "humano"
        jugador_blanco = cuerpo.get("jugador_blanco") or "humano"

        tiempo_limite = int(cuerpo.get("tiempo_limite_ms", 5000))
        # El MCTS de Lina es más lento por simulación: en duelo se usa un
        # presupuesto menor por jugada para mantener partidas ágiles.
        if modo == "duelo":
            tiempo_limite = min(tiempo_limite, 2000)

        config = {
            "simulaciones": simulaciones,
            "modo": modo,
            "tiempo_limite_ms": tiempo_limite,
        }
        jugadores = {NEGRO: jugador_negro, BLANCO: jugador_blanco}

        if modo == "vs_ia":
            jugadores[BLANCO] = f"mcts-{simulaciones}"
        elif modo == "ia_ia":
            jugadores[NEGRO] = f"mcts-{simulaciones}"
            jugadores[BLANCO] = f"mcts-{simulaciones}"
        elif modo == "duelo":
            for color, lado in ((NEGRO, jugador_negro), (BLANCO, jugador_blanco)):
                if lado in (None, "humano"):
                    jugadores[color] = "humano"
                elif lado.startswith("lina-"):
                    jugadores[color] = lado
                elif lado.startswith("mcts-"):
                    jugadores[color] = lado
                else:
                    return jsonify({"error": f"jugador inválido: {lado}"}), 400

        identificador = store.generar_id()
        partida = Partida(tamano, komi)
        with _CANDADO:
            PARTIDAS[identificador] = SesionPartida(
                identificador, partida, jugadores, modo, config)
        return jsonify(_estado_sesion(PARTIDAS[identificador]))

    @app.post("/api/game/<identificador>/move")
    def _jugar(identificador):
        sesion = _obtener_sesion(identificador)
        cuerpo = request.get_json(silent=True) or {}
        fila = int(cuerpo.get("fila", -1))
        col = int(cuerpo.get("col", -1))
        tiempo_ms = sesion.medir_tiempo_jugador()
        info = sesion.partida.jugar(fila, col)
        sesion.partida.agregar_metadatos_ultimo_movimiento(
            {"tiempo_ms": tiempo_ms})
        _enriquecer_perf(sesion)
        return _respuesta_movimiento(sesion, info)

    @app.post("/api/game/<identificador>/pass")
    def _pasar(identificador):
        sesion = _obtener_sesion(identificador)
        tiempo_ms = sesion.medir_tiempo_jugador()
        sesion.partida.pasar()
        sesion.partida.agregar_metadatos_ultimo_movimiento(
            {"tiempo_ms": tiempo_ms, "perf": {"api_ms": _tiempo_ultima_api()}})
        return _respuesta_movimiento(sesion, {"tipo": "pase"})

    @app.post("/api/game/<identificador>/resign")
    def _rendirse(identificador):
        sesion = _obtener_sesion(identificador)
        cuerpo = request.get_json(silent=True) or {}
        color = cuerpo.get("color")
        if color is not None:
            sesion.partida.rendirse(simbolo_a_color(color))
        else:
            sesion.partida.rendirse()
        store.guardar_partida(sesion.partida, sesion.jugadores,
                              {**sesion.config, "id": sesion.id})
        PARTIDAS.pop(sesion.id, None)
        return jsonify(_estado_sesion(sesion))

    @app.post("/api/game/<identificador>/ai-move")
    def _movimiento_ia(identificador):
        sesion = _obtener_sesion(identificador)
        if sesion.partida.terminada:
            return jsonify(_estado_sesion(sesion))

        color = sesion.turno_actual()
        cuerpo = request.get_json(silent=True) or {}
        simulaciones = int(cuerpo.get("simulaciones", sesion.config["simulaciones"]))
        config_ia = sesion.jugadores.get(color, "")
        inicio = time.perf_counter()

        if es_config_lina(config_ia):
            from ai.rival_lina import crear_rival
            jugador = crear_rival(
                simulaciones=int(config_ia.split("-")[1]),
                tiempo_limite_ms=sesion.config.get("tiempo_limite_ms"))
            resultado = jugador.mejor_jugada(sesion.partida)
        else:
            mcts = crear_mcts(simulaciones=simulaciones,
                              tiempo_limite_ms=sesion.config.get("tiempo_limite_ms"))
            resultado = mcts.mejor_jugada(sesion.partida)
        tiempo_total_ms = (time.perf_counter() - inicio) * 1000

        info = None
        if resultado["pase"]:
            sesion.partida.pasar()
        else:
            info = sesion.partida.jugar(resultado["fila"], resultado["col"])

        datos_ia = {
            "sims": resultado["sims"],
            "time_ms": round(resultado["tiempo_ms"], 2),
            "win_rate": resultado["win_rate"],
            "nodes": resultado["nodes"],
            "config": resultado["config"],
            "policy_confidence": None,
            "value_estimate": None,
        }
        sesion.partida.agregar_metadatos_ultimo_movimiento(
            {"ai": datos_ia, "tiempo_ms": round(tiempo_total_ms, 2)})
        perf.registrar_ia({
            "config": resultado["config"],
            "sims": resultado["sims"],
            "time_ms": round(tiempo_total_ms, 2),
            "nodes": resultado["nodes"],
            "win_rate": resultado["win_rate"],
        })
        _enriquecer_perf(sesion)
        return _respuesta_movimiento(sesion, info or {"tipo": "pase"})

    @app.post("/api/game/<identificador>/analysis")
    def _analizar(identificador):
        sesion = _obtener_sesion(identificador)
        cuerpo = request.get_json(silent=True) or {}
        simulaciones = int(cuerpo.get("simulaciones", sesion.config["simulaciones"]))
        n = max(1, min(10, int(cuerpo.get("top", 5))))
        inicio = time.perf_counter()
        mcts = crear_mcts(simulaciones=simulaciones,
                          tiempo_limite_ms=sesion.config.get("tiempo_limite_ms"))
        analisis = mcts.analizar(sesion.partida, n=n)
        analisis["tiempo_total_ms"] = round((time.perf_counter() - inicio) * 1000, 2)
        return jsonify({
            "id": sesion.id,
            "turno": color_a_simbolo(sesion.turno_actual()),
            "modo": sesion.modo,
            "analisis": analisis,
        })

    @app.get("/api/game/<identificador>")
    def _ver_partida(identificador):
        sesion = PARTIDAS.get(identificador)
        if sesion is None:
            return jsonify(store.cargar_partida(identificador))
        if sesion.partida.terminada:
            try:
                return jsonify(store.cargar_partida(identificador))
            except FileNotFoundError:
                pass
        return jsonify(_estado_sesion(sesion))

    @app.get("/api/games")
    def _listar():
        return jsonify({"partidas": store.listar_partidas()})

    @app.post("/api/ai/experiment")
    def _experimento():
        cuerpo = request.get_json(silent=True) or {}
        negro = cuerpo.get("negro", "mcts-250")
        blanco = cuerpo.get("blanco", "mcts-250")
        partidas = max(1, min(20, int(cuerpo.get("partidas", 2))))
        tiempo_limite_ms = int(cuerpo.get("tiempo_limite_ms", 1500))
        limite_movimientos = int(cuerpo.get("limite_movimientos", 360))

        inicio = time.perf_counter()
        from ai.experimento import experimento
        datos = experimento(negro, blanco, partidas=partidas,
                            tiempo_limite_ms=tiempo_limite_ms,
                            limite_movimientos=limite_movimientos)
        datos["tiempo_total_ms"] = round((time.perf_counter() - inicio) * 1000, 2)
        perf.registrar_medicion({"tipo": "experimento", **datos})
        return jsonify(datos)

    @app.get("/api/metrics")
    def _metricas():
        return jsonify({
            **store.calcular_rankings(),
            **store.obtener_estadisticas_ia(),
            "experimentos": perf.obtener_experimentos(),
        })

    @app.get("/api/perf")
    def _desempeno():
        return jsonify(perf.resumen_perf())

    return app


def _obtener_sesion(identificador: str) -> SesionPartida:
    sesion = PARTIDAS.get(identificador)
    if sesion is None:
        raise FileNotFoundError(f"la partida {identificador} no existe")
    return sesion


def _tiempo_ultima_api() -> float:
    return round((time.perf_counter() - g._inicio) * 1000, 2)


def _enriquecer_perf(sesion: SesionPartida) -> None:
    sesion.partida.agregar_metadatos_ultimo_movimiento(
        {"perf": {"api_ms": _tiempo_ultima_api()}})


def _respuesta_movimiento(sesion: SesionPartida, info) -> Flask.response_class:
    terminada = sesion.partida.terminada
    if terminada and not sesion.config.get("guardada"):
        store.guardar_partida(sesion.partida, sesion.jugadores,
                              {**sesion.config, "id": sesion.id})
        sesion.config["guardada"] = True
    if terminada:
        # liberar la sesión: la partida ya está persistida en disco
        PARTIDAS.pop(sesion.id, None)
    return jsonify({
        "info": info,
        "estado": _estado_sesion(sesion),
    })


def _estado_sesion(sesion: SesionPartida) -> dict:
    partida = sesion.partida
    return {
        "id": sesion.id,
        "modo": sesion.modo,
        "tamano": partida.tamano,
        "komi": partida.komi,
        "jugadores": {
            color_a_simbolo(c): sesion.jugadores.get(c) for c in (NEGRO, BLANCO)
        },
        "config": sesion.config,
        **partida.obtener_estado(),
        "movimientos": partida.registro,
    }


app = crear_app()


if __name__ == "__main__":
    store._asegurar_directorios()
    perf.cargar_log()
    app.run(debug=True, port=5000, use_reloader=False)