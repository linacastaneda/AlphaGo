"""Redes policy/value en PyTorch y export a ONNX.

La arquitectura sigue la convención de AlphaGo simplificado del proyecto:
CNN pequeña compartida con dos cabezas (política y valor). Solo se necesita
en el entorno de entrenamiento (Google Colab / requirements-train.txt).

ENTRADA:  canales = ai.redes.codificar(tablero, color) → (5, 9, 9)
POLÍTICA: logits crudos de 82 (81 intersecciones + 1 pase). La inferencia
          (ai/redes.py) aplica el softmax sobre las jugadas legales.
VALOR:    sigmoide → probabilidad de que el color a mover gane la partida.
"""

import random
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F

#: canales de entrada: PROPIO, OPO, ATARI_PROPIO, ATARI_OPO, CONSTANTE
CANALES_ENTRADA = 5
TAMANO_BASE = 9


def tamano_salida_politica(tamano: int = TAMANO_BASE) -> int:
    return tamano * tamano + 1


class RedesAlphaGo(nn.Module):
    """CNN compartida (3 conv 3×3 + BN + ReLU) con cabezas de política y valor."""

    def __init__(self, tamano: int = TAMANO_BASE, canales_conv: int = 32):
        super().__init__()
        self.tamano = tamano
        self.canales_conv = canales_conv

        self.cuerpo = nn.Sequential(
            nn.Conv2d(CANALES_ENTRADA, canales_conv, 3, padding=1),
            nn.BatchNorm2d(canales_conv),
            nn.ReLU(inplace=True),
            nn.Conv2d(canales_conv, canales_conv, 3, padding=1),
            nn.BatchNorm2d(canales_conv),
            nn.ReLU(inplace=True),
            nn.Conv2d(canales_conv, canales_conv, 3, padding=1),
            nn.BatchNorm2d(canales_conv),
            nn.ReLU(inplace=True),
        )

        self.cabeza_politica = nn.Sequential(
            nn.Conv2d(canales_conv, canales_conv, 1),
            nn.BatchNorm2d(canales_conv),
            nn.ReLU(inplace=True),
            nn.Conv2d(canales_conv, tamano * tamano + 1, 1),
        )

        self.cabeza_valor = nn.Sequential(
            nn.Conv2d(canales_conv, 1, 1),
            nn.BatchNorm2d(1),
            nn.ReLU(inplace=True),
            nn.Flatten(),
            nn.Linear(tamano * tamano, 64),
            nn.ReLU(inplace=True),
            nn.Linear(64, 1),
            nn.Sigmoid(),
        )

    def forward(self, X):
        """Devuelve ``(logits_politica, valor)`` con forma (N,82) y (N,1)."""
        caracteristicas = self.cuerpo(X)
        logits = self.cabeza_politica(caracteristicas)
        logits = logits.reshape(X.size(0), -1)
        valor = self.cabeza_valor(caracteristicas)
        return logits, valor


class _SoloPolitica(nn.Module):
    """Envoltorio que expone solo la cabeza de política (para exportar ONNX)."""

    def __init__(self, modelo: RedesAlphaGo):
        super().__init__()
        self.modelo = modelo

    def forward(self, X):
        logits = self.modelo.cabeza_politica(self.modelo.cuerpo(X))
        return logits.reshape(X.size(0), -1)


class _SoloValor(nn.Module):
    """Envoltorio que expone solo la cabeza de valor (para exportar ONNX)."""

    def __init__(self, modelo: RedesAlphaGo):
        super().__init__()
        self.modelo = modelo

    def forward(self, X):
        return self.modelo.cabeza_valor(self.modelo.cuerpo(X))


def crear_lotes(muestras: list, tamano_lote: int, semilla: int = 42):
    """Genera lotes (X, y_politica, y_valor, mascara_valor) a partir de muestras."""
    indices = list(range(len(muestras)))
    random.Random(semilla).shuffle(indices)
    for inicio in range(0, len(indices), tamano_lote):
        lote = [muestras[i] for i in indices[inicio:inicio + tamano_lote]]
        X = torch.from_numpy(np.stack([m["canal"] for m in lote])).float()
        y_politica = torch.tensor([m["etiqueta_politica"] for m in lote],
                                  dtype=torch.long)
        y_valor = torch.tensor(
            [0.0 if m["etiqueta_valor"] is None else m["etiqueta_valor"]
             for m in lote], dtype=torch.float32).unsqueeze(1)
        mascara = torch.tensor([m["etiqueta_valor"] is not None for m in lote],
                               dtype=torch.bool)
        yield X, y_politica, y_valor, mascara


def paso_entrenamiento(modelo, lote, optimizador):
    """Un paso de descenso: loss = CE(política) + BCE(valor sobre muestras con resultado)."""
    X, y_politica, y_valor, mascara = lote
    modelo.train()
    optimizador.zero_grad()
    logits, valor = modelo(X)

    loss_politica = F.cross_entropy(logits, y_politica)
    perdida_valor = 0.0
    if mascara.any():
        perdida_valor = F.binary_cross_entropy(valor[mascara], y_valor[mascara])
    loss = loss_politica + perdida_valor

    loss.backward()
    optimizador.step()

    con_mover = (logits.argmax(dim=1) == y_politica).float().mean().item()
    return {"loss": loss.item(), "perdida_politica": loss_politica.item(),
            "perdida_valor": perdida_valor.item() if torch.is_tensor(perdida_valor) else 0.0,
            "precision": con_mover}


def entrenar(modelo, muestras, epochs: int = 3, tamano_lote: int = 128,
             lr: float = 1e-3, semilla: int = 42, verbose: bool = True) -> dict:
    """Entrena el modelo con las muestras del dataset y devuelve el historial."""
    optimizador = torch.optim.Adam(modelo.parameters(), lr=lr)
    historial = {"loss": [], "perdida_politica": [], "perdida_valor": [],
                 "precision": []}
    for epoca in range(1, epochs + 1):
        lista_indices = list(range(len(muestras)))
        random.Random(semilla + epoca).shuffle(lista_indices)
        lista_epoca = [muestras[i] for i in lista_indices]
        dispositivo = next(modelo.parameters()).device
        suma = {clave: 0.0 for clave in historial}
        contador = 0
        for lote in crear_lotes(lista_epoca, tamano_lote, epoca):
            lote = tuple(t.to(dispositivo) for t in lote)
            metricas = paso_entrenamiento(modelo, lote, optimizador)
            for clave in historial:
                historial[clave].append(metricas[clave])
                suma[clave] += metricas[clave]
            contador += 1
        if verbose and contador:
            print(f"época {epoca}: loss {suma['loss'] / contador:.4f} · "
                  f"precisión política {suma['precision'] / contador:.3f}")
    return historial


def exportar_onnx(modelo, directorio, tamano: int = TAMANO_BASE):
    """Exporta policy.onnx y value.onnx al directorio (entrada dinámica en batch)."""
    directorio = Path(directorio)
    directorio.mkdir(parents=True, exist_ok=True)
    modelo.eval()
    X = torch.zeros(1, CANALES_ENTRADA, tamano, tamano)
    ejes_dinamicos = {"X": {0: "batch"}}

    torch.onnx.export(
        _SoloPolitica(modelo), X, str(directorio / "policy.onnx"),
        input_names=["X"], output_names=["politica"], opset_version=14,
        dynamic_axes={**ejes_dinamicos, "politica": {0: "batch"}})
    torch.onnx.export(
        _SoloValor(modelo), X, str(directorio / "value.onnx"),
        input_names=["X"], output_names=["valor"], opset_version=14,
        dynamic_axes={**ejes_dinamicos, "valor": {0: "batch"}})
    return directorio