"""Descarga opcional de partidas SGF 9×9 públicas.

Si la red no está disponible, no es problema: el parser acepta cualquier
SGF colocado a mano en ``data/historical/`` (según el plan).
"""

import sys
import urllib.request
from pathlib import Path

_RUTA_BASE = Path(__file__).resolve().parent.parent
if str(_RUTA_BASE) not in sys.path:
    sys.path.insert(0, str(_RUTA_BASE))
from entrenamiento.dataset import RUTA_HISTORICAL

_FUENTES = []


def descargar_si_disponible(directorio=None, salida=sys.stdout, fuentes=None) -> bool:
    """Intenta descargar SGFs de referencia; True si al menos uno se guardó.

    Pasa tus URLs reales mediante ``fuentes=[...]``; por defecto no hay
    ninguna (evita depender de alojamientos que pueden desaparecer). Siempre
    es válido dejar los archivos a mano en ``data/historical/``.
    """
    directorio = Path(directorio) if directorio is not None else RUTA_HISTORICAL
    directorio.mkdir(parents=True, exist_ok=True)
    fuentes = fuentes if fuentes is not None else _FUENTES
    guardados = 0

    if not fuentes:
        salida.write(
            "[descarga] sin fuentes configuradas: añade URLs con fuentes=[...]\n"
            "  o deposita SGF 9x9 directamente en data/historical/\n")

    for i, url in enumerate(fuentes):
        try:
            with urllib.request.urlopen(url, timeout=15) as respuesta:
                contenido = respuesta.read().decode("utf-8", errors="ignore")
        except Exception as err:
            salida.write(f"[descarga] fuente {url} no disponible: {err}\n")
            continue
        if not contenido.strip().startswith("("):
            salida.write(f"[descarga] fuente {url} no era SGF válido\n")
            continue
        ruta = directorio / f"referencia_{i:02d}.sgf"
        ruta.write_text(contenido, encoding="utf-8")
        guardados += 1
        salida.write(f"[descarga] guardado: {ruta}\n")

    salida.write(f"[descarga] SGF guardados: {guardados}\n")
    return guardados > 0


def main() -> None:
    descargar_si_disponible()
    from entrenamiento.dataset import resumen_texto
    print(resumen_texto())


if __name__ == "__main__":
    main()