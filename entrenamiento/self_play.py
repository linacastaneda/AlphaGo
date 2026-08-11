"""Self-play: la IA se enfrenta a sí misma y genera partidas SGF.

Las partidas generadas alimentan ``data/historical/`` (o ``data/training/``)
y de ahí el entrenamiento supervisado de las redes (Fase C).
"""

import argparse
import uuid
from pathlib import Path

from ia.experimento import construir_ia, jugar_partida
from motor import color_a_simbolo

RUTA_BASE = Path(__file__).resolve().parent.parent
DIRECTORIO_TRAINING = RUTA_BASE / "data" / "training"
DIRECTORIO_HISTORICAL = RUTA_BASE / "data" / "historical"


def _letras_sgf():
    return "abcdefghjklmnopqrstuvwxyz"


def _coord_a_sgf(fila: int, col: int) -> str:
    letras = _letras_sgf()
    return letras[fila] + letras[col]


def _resultado_a_re(resultado: dict | None) -> str:
    if not resultado:
        return "0"
    ganador = resultado.get("ganador")
    if ganador is None:
        return "0"
    simbolo = color_a_simbolo(ganador)
    if resultado.get("por_rendicion"):
        return f"{simbolo}+R"
    margen = resultado.get("margen")
    return f"{simbolo}+{margen}" if margen is not None else f"{simbolo}+?"


def generar_sgf(config_negro=None, config_blanco=None, semilla: int | None = None,
                limite_movimientos: int = 360) -> dict:
    """Juega una partida de IA contra IA y devuelve su representación SGF.

    Resultado: dict con ``sgf`` (texto), ``configs`` y ``resultado``.
    """
    config_negro = config_negro or "mcts-50"
    config_blanco = config_blanco or config_negro
    movimientos = []
    resultado_sgf = None

    def al_jugar(color, jugada, tiempo_ms):
        nonlocal resultado_sgf
        simbolo = color_a_simbolo(color)
        if jugada.get("pase"):
            movimientos.append(f"{simbolo}[]")
        else:
            movimientos.append(f"{simbolo}[{_coord_a_sgf(jugada['fila'], jugada['col'])}]")

    resumen = jugar_partida(
        construir_ia(config_negro),
        construir_ia(config_blanco),
        semilla=semilla,
        limite_movimientos=limite_movimientos,
        al_jugar=al_jugar)

    # si el final fue por límite de movimientos (o no cerró en doble pase),
    # añadimos dos pases para que la partida SGF quede cerrada de forma válida
    ultimos = movimientos[-2:]
    if not (len(ultimos) == 2 and ultimos[0].endswith("[]") and ultimos[1].endswith("[]")):
        siguiente = "B[]" if len(movimientos) % 2 == 0 else "W[]"
        movimientos.append(siguiente)
        movimientos.append("W[]" if siguiente == "B[]" else "B[]")

    cuerpo = "".join(";" + m for m in movimientos)
    sgf = (f"(;GM[1]FF[4]SZ[9]KM[7.5]PB[{config_negro}]"
           f"PW[{config_blanco}]RE[{_resultado_a_re(resumen['resultado'])}]{cuerpo})")
    return {
        "sgf": sgf,
        "config_negro": config_negro,
        "config_blanco": config_blanco,
        "ganador": resumen["ganador"],
        "num_movimientos": resumen["num_movimientos"],
    }


def generar_muchas(partidas: int = 4, config=None, directorio=None,
                   semilla_inicial: int | None = 1) -> list:
    """Genera ``partidas`` autojuegos y los guarda como SGF en el directorio."""
    directorio = Path(directorio) if directorio is not None else DIRECTORIO_HISTORICAL
    directorio.mkdir(parents=True, exist_ok=True)
    config = config or "mcts-50"
    rutas = []
    for i in range(partidas):
        partida = generar_sgf(
            config_negro=config, config_blanco=config,
            semilla=semilla_inicial + i if semilla_inicial is not None else None)
        ruta = directorio / f"{uuid.uuid4().hex[:10]}.sgf"
        ruta.write_text(partida["sgf"], encoding="utf-8")
        rutas.append(ruta)
    return rutas


def main() -> None:
    import sys
    if str(RUTA_BASE) not in sys.path:
        sys.path.insert(0, str(RUTA_BASE))

    parser = argparse.ArgumentParser(description="Self-play: genera partidas IA vs IA en SGF")
    parser.add_argument("--partidas", type=int, default=4)
    parser.add_argument("--config", default="mcts-50")
    parser.add_argument("--dir", default=str(DIRECTORIO_HISTORICAL))
    parser.add_argument("--semilla", type=int, default=1)
    opciones = parser.parse_args()

    rutas = generar_muchas(opciones.partidas, opciones.config,
                           Path(opciones.dir), opciones.semilla)
    print(f"generadas {len(rutas)} partidas en {opciones.dir}")


if __name__ == "__main__":
    main()