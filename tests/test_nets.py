"""Tests de las redes policy/value (se saltan si PyTorch no está instalado)."""

import pytest

torch = pytest.importorskip("torch")

from training.nets import (CANALES_ENTRADA, RedesAlphaGo, crear_lotes,
                           entrenar, exportar_onnx, paso_entrenamiento,
                           tamano_salida_politica)


def _muestras_sinteticas(n: int) -> list:
    """muestras pequeñas y variadas para probar formas y descenso del gradiente."""
    muestras = []
    for i in range(n):
        canal = torch.zeros(CANALES_ENTRADA, 9, 9)
        canal[0, i % 9, (i * 3) % 9] = 1.0
        muestras.append({
            "canal": canal.numpy(),
            "etiqueta_politica": (i * 7) % tamano_salida_politica(),
            "etiqueta_valor": 1.0 if i % 2 == 0 else 0.0,
        })
    return muestras


def test_formas_forward():
    modelo = RedesAlphaGo(tamano=9, canales_conv=8)
    X = torch.randn(4, CANALES_ENTRADA, 9, 9)
    logits, valor = modelo(X)
    assert logits.shape == (4, 82)
    assert valor.shape == (4, 1)
    assert float(valor.min()) >= 0.0 and float(valor.max()) <= 1.0


def test_paso_entrenamiento_reduce_perdida():
    modelo = RedesAlphaGo(tamano=9, canales_conv=8)
    optimizador = torch.optim.Adam(modelo.parameters(), lr=1e-2)
    lote = next(crear_lotes(_muestras_sinteticas(16), 16, semilla=1))
    antes = paso_entrenamiento(modelo, lote, optimizador)["loss"]
    for _ in range(10):
        despues = paso_entrenamiento(modelo, lote, optimizador)["loss"]
    assert despues < antes


def test_entrenar_devuelve_historial():
    modelo = RedesAlphaGo(tamano=9, canales_conv=8)
    historial = entrenar(modelo, _muestras_sinteticas(32), epochs=2,
                         tamano_lote=16, verbose=False)
    assert set(historial) == {"loss", "perdida_politica", "perdida_valor",
                              "precision"}
    assert all(isinstance(v, list) and v for v in historial.values())


def test_exportar_onnx(tmp_path):
    modelo = RedesAlphaGo(tamano=9, canales_conv=8)
    exportar_onnx(modelo, tmp_path)
    assert (tmp_path / "policy.onnx").exists()
    assert (tmp_path / "value.onnx").exists()

    import onnxruntime
    entrada = {
        "X": torch.randn(2, CANALES_ENTRADA, 9, 9).numpy().astype("float32")}
    politica = onnxruntime.InferenceSession(
        str(tmp_path / "policy.onnx"), providers=["CPUExecutionProvider"])
    valor = onnxruntime.InferenceSession(
        str(tmp_path / "value.onnx"), providers=["CPUExecutionProvider"])
    y_politica = politica.run(None, entrada)[0]
    y_valor = valor.run(None, entrada)[0]
    assert y_politica.shape == (2, 82)
    assert y_valor.shape == (2, 1)