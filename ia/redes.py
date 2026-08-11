"""Redes policy/value: codificación del tablero e inferencia ONNX.

Si no hay modelos exportados (o no está instalado onnxruntime), `cargar_redes`
devuelve ``None``: el MCTS sigue funcionando con su baseline heurístico.
"""

from pathlib import Path

import numpy

from motor import BLANCO, NEGRO, VACIO

RUTA_BASE = Path(__file__).resolve().parent.parent
DIRECTORIO_MODELOS = RUTA_BASE / "models"

CANALES = 5


def _softmax(entrada: numpy.ndarray) -> numpy.ndarray:
    exp = numpy.exp(entrada - entrada.max())
    return exp / exp.sum()


def codificar(tablero, color: int) -> numpy.ndarray:
    """Codifica la posición en CANALES planos (matriz de puntos por color).

    Canales: piedras propias, piedras del oponente, atari propia,
    atari del oponente y una constante de normalización.
    """
    n = tablero.tamano
    matriz = tablero.celdas
    oponente = NEGRO if color == BLANCO else BLANCO

    propio = numpy.zeros((n, n), dtype=numpy.float32)
    opo = numpy.zeros((n, n), dtype=numpy.float32)
    for f in range(n):
        for c in range(n):
            celda = matriz[f][c]
            if celda == color:
                propio[f][c] = 1.0
            elif celda == oponente:
                opo[f][c] = 1.0

    atari_propio = numpy.zeros((n, n), dtype=numpy.float32)
    atari_opo = numpy.zeros((n, n), dtype=numpy.float32)
    for (f, c), info in tablero.grupos_con_libertades().items():
        if info["libertades"] == 1:
            if info["color"] == color:
                atari_propio[f][c] = 1.0
            elif info["color"] == oponente:
                atari_opo[f][c] = 1.0

    constantes = numpy.ones((n, n), dtype=numpy.float32)
    return numpy.stack([propio, opo, atari_propio, atari_opo, constantes])


class RedesGo:
    """Fachada de inferencia: política (softmax N*N+1) y valor (sigmoide).

    ``f_politica`` y ``f_valor`` son callables que reciben el tensor codificado
    y devuelven la salida cruda del modelo (logits de política, valor escalar).
    """

    def __init__(self, tamano: int, f_politica, f_valor):
        self.tamano = tamano
        self._f_politica = f_politica
        self._f_valor = f_valor

    def distribucion_politica(self, tablero, color: int):
        """Devuelve ``(movimientos_legales, {clave: probabilidad})``.

        La clave del pase es ``("pase",)`` (también exportada por el MCTS).
        """
        movimientos = tablero.obtener_movimientos_legales(color)
        X = codificar(tablero, color)[numpy.newaxis]
        logits = numpy.asarray(self._f_politica(X), dtype=numpy.float32).ravel()
        probs = _softmax(logits)

        n = self.tamano
        salida = {}
        indice_total = n * n + 1
        if logits.shape[0] >= indice_total:
            salida[("pase",)] = float(probs[-1])
        for fila, col in movimientos:
            indice = fila * n + col
            salida[(fila, col)] = float(probs[indice])

        # renormaleza sobre las jugadas legales (prior tipo AlphaZero)
        total = sum(salida.values())
        if total > 0:
            salida = {clave: v / total for clave, v in salida.items()}
        return movimientos, salida

    def estimar_valor(self, tablero, color: int) -> float:
        """Probabilidad estimada (0..1) de que ``color`` gane la posición."""
        X = codificar(tablero, color)[numpy.newaxis]
        salida = numpy.asarray(self._f_valor(X), dtype=numpy.float32).ravel()
        v = float(salida.reshape(-1)[0])
        return max(0.0, min(1.0, v))


def _abrir_modelo(ruta: Path):
    """Abre un modelo ONNX o devuelve None si no es accesible."""
    if not ruta.exists():
        return None
    try:
        import onnxruntime
        return onnxruntime.InferenceSession(str(ruta), providers=["CPUExecutionProvider"])
    except (OSError, ImportError, RuntimeError):
        return None


def cargar_redes(directorio=None) -> RedesGo | None:
    """Carga policy.onnx + value.onnx del directorio; ``None`` si faltan."""
    directorio = Path(directorio) if directorio is not None else DIRECTORIO_MODELOS
    politica = _abrir_modelo(directorio / "policy.onnx")
    valor = _abrir_modelo(directorio / "value.onnx")
    if politica is None or valor is None:
        return None

    def _inferir_politica(X):
        salida = politica.run(None, {politica.get_inputs()[0].name: X})
        return numpy.asarray(salida[0], dtype=numpy.float32)

    def _inferir_valor(X):
        salida = valor.run(None, {valor.get_inputs()[0].name: X})
        return numpy.asarray(salida[0], dtype=numpy.float32)

    return RedesGo(9, _inferir_politica, _inferir_valor)