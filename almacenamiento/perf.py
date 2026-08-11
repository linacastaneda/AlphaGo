"""Métricas de rendimiento de la propia aplicación (log rodante)."""

import json
import threading
import time
from collections import deque
from pathlib import Path


RUTA_LOG = Path(__file__).resolve().parent.parent / "data" / "perf.json"
MAX_ENTRADAS = 2000
_INTERVALO_PERSISTENCIA = 200

_cerrojo = threading.Lock()
_mediciones = deque(maxlen=MAX_ENTRADAS)
_contador = 0


def registrar_medicion(entrada: dict) -> None:
    """Registra una medición de rendimiento (latencia, memoria, IA...)."""
    global _contador
    entrada = dict(entrada)
    entrada.setdefault("timestamp", time.time())
    with _cerrojo:
        _mediciones.append(entrada)
        _contador += 1
        if _contador % _INTERVALO_PERSISTENCIA == 0:
            _persistir()


def registrar_latencia_endpoint(endpoint: str, tiempo_ms: float, status: int = 200) -> None:
    registrar_medicion({
        "tipo": "endpoint",
        "endpoint": endpoint,
        "tiempo_ms": round(tiempo_ms, 3),
        "status": status,
    })


def registrar_ia(detalles: dict) -> None:
    registrar_medicion({"tipo": "ia", **detalles})


def registrar_memoria(memoria_kb: float) -> None:
    registrar_medicion({"tipo": "memoria", "memoria_kb": round(memoria_kb, 1)})


def obtener_mediciones() -> list:
    with _cerrojo:
        return list(_mediciones)


def obtener_experimentos(limite: int = 10) -> list:
    """Últimos resultados de experimentos comparativos de IA."""
    with _cerrojo:
        return [m for m in reversed(_mediciones) if m["tipo"] == "experimento"][:limite]


def _percentil(valores: list, pct: float):
    if not valores:
        return 0.0
    ordenados = sorted(valores)
    indice = min(len(ordenados) - 1, int(len(ordenados) * pct))
    return round(ordenados[indice], 3)


def resumen_perf() -> dict:
    """Agrega las mediciones: latencia por endpoint, IA y memoria."""
    mediciones = obtener_mediciones()
    por_endpoint = {}
    ia = []
    memoria = []
    max_memoria = 0.0

    for m in mediciones:
        if m["tipo"] == "endpoint":
            ep = m["endpoint"]
            if ep not in por_endpoint:
                por_endpoint[ep] = []
            por_endpoint[ep].append(m["tiempo_ms"])
        elif m["tipo"] == "ia":
            ia.append(m)
        elif m["tipo"] == "memoria":
            memoria.append(m["memoria_kb"])

    endpoint_resumen = {}
    for ep, valores in por_endpoint.items():
        endpoint_resumen[ep] = {
            "count": len(valores),
            "promedio_ms": round(sum(valores) / len(valores), 3),
            "p95_ms": _percentil(valores, 0.95),
            "max_ms": round(max(valores), 3),
            "min_ms": round(min(valores), 3),
        }

    if memoria and memoria[-1] > 0:
        max_memoria = max(max(memoria), 0)

    return {
        "endpoints": endpoint_resumen,
        "ia": ia[-200:],
        "memoria_promedio_kb": round(sum(memoria) / len(memoria), 1) if memoria else 0,
        "max_memoria_kb": round(max_memoria, 1) if max_memoria else 0,
        "total_mediciones": len(mediciones),
    }


def _persistir() -> None:
    """Escribe el log rodante a disco de forma tolerante a fallos.

    La persistencia nunca debe interrumpir el request: en entornos con
    filesystem efímero o de solo lectura (p. ej. Render) el fallo se ignora.
    """
    try:
        RUTA_LOG.parent.mkdir(parents=True, exist_ok=True)
        with _cerrojo:
            datos = list(_mediciones)
        temporal = RUTA_LOG.with_suffix(".tmp")
        with open(temporal, "w", encoding="utf-8") as archivo:
            json.dump({"mediciones": datos}, archivo)
        temporal.replace(RUTA_LOG)
    except OSError:
        pass


def cargar_log() -> None:
    """Restaura el log rodante desde disco si existe."""
    global _mediciones
    if not RUTA_LOG.exists():
        return
    try:
        with open(RUTA_LOG, "r", encoding="utf-8") as archivo:
            datos = json.load(archivo)
        with _cerrojo:
            _mediciones = deque(datos.get("mediciones", [])[-MAX_ENTRADAS:], maxlen=MAX_ENTRADAS)
    except (json.JSONDecodeError, OSError):
        pass