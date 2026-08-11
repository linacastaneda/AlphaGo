"""Motor del juego de Go."""

NEGRO = 1
BLANCO = 2
VACIO = 0

SIMBOLOS_COLOR = {NEGRO: "B", BLANCO: "W"}
NOMBRES_COLOR = {NEGRO: "negro", BLANCO: "blanco"}


def color_a_simbolo(color: int) -> str:
    """Convierte el color interno (1 negro, 2 blanco) al símbolo estándar B/W."""
    return SIMBOLOS_COLOR[color]


def simbolo_a_color(simbolo: str) -> int:
    """Convierte el símbolo estándar B/W al color interno."""
    return {v: k for k, v in SIMBOLOS_COLOR.items()}[simbolo.upper()]


def oponer(color: int) -> int:
    """Devuelve el color contrario (negro<->blanco)."""
    return BLANCO if color == NEGRO else NEGRO