"""Dataset de entrenamiento: parser SGF y codificación de posiciones.

Convierte partidas SGF 9×9 en muestras (canales, etiqueta de política y
etiqueta de valor) listas para entrenar las redes policy/value.
"""

import re
from pathlib import Path

from engine import BLANCO, NEGRO
from engine.scoring import Partida
from ai.redes import codificar

RUTA_HISTORICAL = Path(__file__).resolve().parent.parent / "data" / "historical"


def _escanear(texto: str):
    """Tokeniza propiedades SGF básicas ``CLAVE[valor]``.

    Salta el contenido de propiedades desconocidas (comentarios, texto libre)
    para no interpretar coordenadas que aparezcan dentro de ellas.
    """
    token = re.compile(r"[A-Za-z]{1,3}")
    i = 0
    n = len(texto)
    while i < n:
        m = token.match(texto, i)
        if not m:
            i += 1
            continue
        nombre = m.group()
        i = m.end()
        if i < n and texto[i] == "[":
            fin = texto.find("]", i)
            valor = texto[i + 1:fin] if fin != -1 else ""
            i = fin + 1 if fin != -1 else n
            yield nombre, valor
        elif nombre:
            yield nombre, ""


def _letras_sgf():
    """Orden de columnas en SGF: a..h, j..z (se omite la 'i')."""
    return "abcdefghjklmnopqrstuvwxyz"


def coord_a_fila_col(txt: str, tamano: int):
    """Convierte una coordenada SGF (ej. 'dd') a (fila, col). None si inválida."""
    if not txt or len(txt) < 2:
        return None
    letras = _letras_sgf()
    try:
        fila = letras.index(txt[0].lower())
        col = letras.index(txt[1].lower())
    except ValueError:
        return None
    if fila >= tamano or col >= tamano:
        return None
    return fila, col


def parsear_sgf(texto: str) -> dict:
    """Extrae cabecera (tamaño, resultado) y secuencia de movimientos.

    Devuelve: ``{tamano, komi, resultado, movimientos: [(color, fila, col)...]}``
    donde el pase es ``(color, None, None)``.
    """
    tamano = 9
    komi = 7.5
    resultado = None
    movimientos = []

    for nombre, valor in _escanear(texto):
        if nombre == "SZ" and valor.isdigit():
            tamano = int(valor)
        elif nombre == "KM":
            try:
                komi = float(valor)
            except ValueError:
                komi = 7.5
        elif nombre == "RE":
            resultado = valor.strip()
        elif nombre in ("B", "W"):
            color = NEGRO if nombre == "B" else BLANCO
            if not valor:
                movimientos.append((color, None, None))
                continue
            pos = coord_a_fila_col(valor, tamano)
            if pos is not None:
                movimientos.append((color, pos[0], pos[1]))

    return {
        "tamano": tamano,
        "komi": komi,
        "resultado": resultado,
        "movimientos": movimientos,
    }


def ganador_de_resultado(texto_resultado: str | None):
    """Devuelve el color ganador ('B'/'W') según RE, o None."""
    if not texto_resultado:
        return None
    primero = texto_resultado.strip()[0].upper()
    if primero in ("B", "W"):
        return primero
    return None


def _etiqueta_valor(ganador: str | None, color: int) -> float | None:
    """Etiqueta de valor: 1 si ``color`` gana la partida, 0 si no."""
    if ganador is None:
        return None
    gano = (ganador == "B") == (color == NEGRO)
    return 1.0 if gano else 0.0


def construir_muestras(partida_sgf: dict) -> list:
    """Convierte una partida parseada en muestras de entrenamiento.

    Cada muestra: canales del tablero (quién va a jugar), etiqueta de política
    (índice de la jugada real, o ``tamano²`` si es pase) y etiqueta de valor
    (1 si el color que juega termina ganando, 0 si no, None si se desconoce).
    """
    if partida_sgf["tamano"] != 9:
        return []
    tamano = partida_sgf["tamano"]
    partida = Partida(tamano, partida_sgf["komi"])
    ganador = ganador_de_resultado(partida_sgf["resultado"])
    muestras = []

    for color, fila, col in partida_sgf["movimientos"]:
        if partida.terminada:
            break
        if fila is not None and not partida.tablero.es_movimiento_legal(fila, col, color):
            # SGF inconsistente con el motor: se omite el movimiento y se sigue
            continue

        muestras.append({
            "color": color,
            "canal": codificar(partida.tablero, color),
            "etiqueta_politica": tamano * tamano if fila is None else fila * tamano + col,
            "etiqueta_valor": _etiqueta_valor(ganador, color),
            "es_pase": fila is None,
        })

        if fila is None:
            partida.pasar()
        else:
            partida.jugar(fila, col)

    return muestras


def cargar_partida_archivo(ruta) -> list:
    """Parsea un archivo SGF y devuelve sus muestras (vacío si se descarta)."""
    try:
        texto = ruta.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    return construir_muestras(parsear_sgf(texto))


def cargar_directorio(directorio=None) -> dict:
    """Carga todas las partidas SGF 9×9 del directorio en muestras."""
    directorio = Path(directorio) if directorio is not None else RUTA_HISTORICAL
    if not directorio.exists():
        return {"muestras": [], "partidas": 0, "descartadas": 0, "errores": []}

    muestras = []
    partidas = 0
    descartadas = 0
    errores = []
    for ruta in sorted(directorio.glob("*.sgf")):
        parcial = cargar_partida_archivo(ruta)
        if parcial:
            partidas += 1
            muestras.extend(parcial)
        else:
            descartadas += 1
            errores.append(str(ruta))
    return {
        "muestras": muestras,
        "partidas": partidas,
        "descartadas": descartadas,
        "errores": errores,
    }


def resumen_texto(directorio=None) -> str:
    datos = cargar_directorio(directorio)
    return (f"partidas 9x9: {datos['partidas']} · muestras: "
            f"{len(datos['muestras'])} · descartadas: {datos['descartadas']}")