"""Almacenamiento: persistencia JSON de partidas, historial y rankings."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from engine import NEGRO, BLANCO, color_a_simbolo, NOMBRES_COLOR
from engine.scoring import Partida


RUTA_BASE = Path(__file__).resolve().parent.parent
DIRECTORIO_PARTIDAS = RUTA_BASE / "data" / "games"
RUTA_HISTORIAL = RUTA_BASE / "data" / "historial.json"


def _asegurar_directorios() -> None:
    DIRECTORIO_PARTIDAS.mkdir(parents=True, exist_ok=True)
    RUTA_HISTORIAL.parent.mkdir(parents=True, exist_ok=True)


def generar_id() -> str:
    return uuid.uuid4().hex[:12]


def serializar_partida(partida: Partida, jugadores: dict, config: dict) -> dict:
    """Convierte una partida jugada en el JSON canónico con coordenadas y métricas."""
    movimientos = []
    for mov in partida.registro:
        entrada = {
            "tipo": mov["tipo"],
            "color": color_a_simbolo(mov["color"]),
            "player": color_a_simbolo(mov["color"]),
            "capturas": mov["capturas"],
            "tiempo_ms": round(mov.get("tiempo_ms") or 0.0, 2),
            "ai": mov.get("ai"),
            "perf": mov.get("perf"),
        }
        entrada["coord"] = mov["coord"]
        movimientos.append(entrada)

    datos = {
        "id": config.get("id") or generar_id(),
        "board_size": partida.tamano,
        "komi": partida.komi,
        "fecha": datetime.now(timezone.utc).isoformat(),
        "jugadores": {
            color_a_simbolo(c): jugadores.get(c, "humano") for c in (NEGRO, BLANCO)
        },
        "config": config,
        "movimientos": movimientos,
        "resultado": partida.resultado,
    }
    return datos


def reconstruir_partida(datos: dict) -> Partida:
    """Reconstruye una Partida re-aplicando las coordenadas guardadas.

    Restaura también el resultado final para que quede idéntica a la original.
    """
    partida = Partida(datos["board_size"], datos["komi"])
    for mov in datos.get("movimientos", []):
        if mov.get("tipo") == "pase":
            partida.pasar()
        else:
            fila, col = mov["coord"]
            partida.jugar(fila, col)
    if datos.get("resultado") and not partida.terminada:
        partida.resultado = datos["resultado"]
        partida.terminada = True
    return partida


def guardar_partida(partida: Partida, jugadores: dict, config: dict) -> dict:
    """Guarda la partida en data/games/<id>.json y actualiza el historial."""
    _asegurar_directorios()
    datos = serializar_partida(partida, jugadores, config)
    ruta = DIRECTORIO_PARTIDAS / f"{datos['id']}.json"
    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump(datos, archivo, ensure_ascii=False, indent=2)
    registrar_en_historial(datos)
    return datos


def cargar_partida(identificador: str) -> dict:
    ruta = DIRECTORIO_PARTIDAS / f"{identificador}.json"
    if not ruta.exists():
        raise FileNotFoundError(f"la partida {identificador} no existe")
    with open(ruta, "r", encoding="utf-8") as archivo:
        return json.load(archivo)


def listar_partidas() -> list:
    """Devuelve un resumen de todas las partidas guardadas, más reciente primero."""
    _asegurar_directorios()
    resumenes = []
    for ruta in DIRECTORIO_PARTIDAS.glob("*.json"):
        try:
            with open(ruta, "r", encoding="utf-8") as archivo:
                datos = json.load(archivo)
        except (json.JSONDecodeError, OSError):
            continue
        resumenes.append(_resumen(datos))

    def _clave_orden(resumen):
        fecha = resumen.get("fecha")
        if fecha:
            try:
                return datetime.fromisoformat(fecha).timestamp()
            except ValueError:
                pass
        return 0.0

    resumenes.sort(key=_clave_orden, reverse=True)
    return resumenes


def _resumen(datos: dict) -> dict:
    resultado = datos.get("resultado") or {}
    ganador = resultado.get("ganador")
    if ganador in (NEGRO, BLANCO):
        ganador = color_a_simbolo(ganador)
    return {
        "id": datos["id"],
        "fecha": datos.get("fecha"),
        "tablero": datos["board_size"],
        "jugadores": datos.get("jugadores", {}),
        "num_movimientos": len(datos.get("movimientos", [])),
        "ganador": ganador,
        "margen": resultado.get("margen"),
        "por_rendicion": resultado.get("por_rendicion", False),
        "terminada": bool(resultado),
    }


def registrar_en_historial(datos: dict) -> None:
    """Añade el resultado de la partida al historial para rankings."""
    _asegurar_directorios()
    historial = _cargar_historial()
    entrada = {
        "id": datos["id"],
        "fecha": datos.get("fecha"),
        "tablero": datos["board_size"],
        "jugadores": datos.get("jugadores", {}),
        "num_movimientos": len(datos.get("movimientos", [])),
        "resultado": datos.get("resultado"),
    }
    historial["partidas"] = [e for e in historial["partidas"] if e["id"] != entrada["id"]]
    historial["partidas"].insert(0, entrada)
    with open(RUTA_HISTORIAL, "w", encoding="utf-8") as archivo:
        json.dump(historial, archivo, ensure_ascii=False, indent=2)


def _cargar_historial() -> dict:
    if not RUTA_HISTORIAL.exists():
        return {"partidas": []}
    with open(RUTA_HISTORIAL, "r", encoding="utf-8") as archivo:
        return json.load(archivo)


def obtener_historial(limite: int = 200) -> dict:
    return _cargar_historial()


def calcular_rankings() -> dict:
    """Calcula victorias, derrotas y win-rate por jugador/configuración de IA."""
    historial = _cargar_historial()
    registros = {}

    for partida in historial["partidas"]:
        resultado = partida.get("resultado") or {}
        ganador = resultado.get("ganador")
        if ganador is None:
            continue
        ganadores = partida.get("jugadores", {})
        # ganador es color interno (1/2); lo traducimos a símbolo
        simbolo_ganador = color_a_simbolo(ganador) if ganador in (NEGRO, BLANCO) else None
        for color_simbolo, nombre in ganadores.items():
            if nombre not in registros:
                registros[nombre] = {"jugador": nombre, "victorias": 0, "derrotas": 0}
            if simbolo_ganador and color_simbolo == simbolo_ganador:
                registros[nombre]["victorias"] += 1
            elif color_simbolo != simbolo_ganador:
                registros[nombre]["derrotas"] += 1

    for datos in registros.values():
        total = datos["victorias"] + datos["derrotas"]
        datos["partidas"] = total
        datos["win_rate"] = round(datos["victorias"] / total, 4) if total else 0.0

    return {"rankings": sorted(registros.values(), key=lambda r: -r["victorias"])}


def obtener_estadisticas_ia() -> dict:
    """Agrega métricas de IA (sims, tiempo, nodos) por configuración desde las partidas."""
    agregados = {}
    for partida in _cargar_historial()["partidas"]:
        datos = None
        try:
            datos = cargar_partida(partida["id"])
        except FileNotFoundError:
            continue
        for mov in datos.get("movimientos", []):
            ia = mov.get("ai") or {}
            if not ia:
                continue
            config = ia.get("config", "desconocido")
            if config not in agregados:
                agregados[config] = {
                    "config": config,
                    "movimientos": 0,
                    "sims": 0,
                    "tiempo_ms": 0.0,
                    "nodos": 0,
                    "sims_por_segundo": 0.0,
                }
            a = agregados[config]
            a["movimientos"] += 1
            a["sims"] += ia.get("sims", 0)
            a["tiempo_ms"] += ia.get("time_ms", 0.0)
            a["nodos"] += ia.get("nodes", 0)

    for a in agregados.values():
        if a["tiempo_ms"] > 0:
            a["sims_por_segundo"] = round(a["sims"] / (a["tiempo_ms"] / 1000.0), 1)
        if a["movimientos"]:
            a["tiempo_promedio_ms"] = round(a["tiempo_ms"] / a["movimientos"], 2)
    return {"estadisticas_ia": list(agregados.values())}