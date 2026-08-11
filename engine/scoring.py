"""Gestión de partidas: turnos, pases, finalización y conteo por área."""

from . import NEGRO, BLANCO, VACIO, oponer
from .board import Tablero


def calcular_puntaje(tablero: Tablero, komi: float = 7.5) -> dict:
    """Conteo por área (chino): piedras en el tablero + territorio vacío.

    Nota: no se retiran piedras muertas automáticamente para esta versión;
    el conteo asume que las piedras sobrevivientes son territorio de cada color.
    """
    tamano = tablero.tamano
    territorio = {NEGRO: 0, BLANCO: 0}
    visitado = set()

    for fila in range(tamano):
        for col in range(tamano):
            if tablero.celdas[fila][col] != VACIO or (fila, col) in visitado:
                continue

            pila = [(fila, col)]
            region = set()
            bordes = set()
            while pila:
                f, c = pila.pop()
                if (f, c) in region:
                    continue
                region.add((f, c))
                for vf, vc in tablero._vecinos(f, c):
                    celda = tablero.celdas[vf][vc]
                    if celda == VACIO and (vf, vc) not in region:
                        pila.append((vf, vc))
                    elif celda != VACIO:
                        bordes.add(celda)

            visitado |= region
            if len(bordes) == 1:
                territorio[list(bordes)[0]] += len(region)

    piedras = {NEGRO: 0, BLANCO: 0}
    for fila in tablero.celdas:
        for celda in fila:
            if celda in piedras:
                piedras[celda] += 1

    total_negro = piedras[NEGRO] + territorio[NEGRO]
    total_blanco = piedras[BLANCO] + territorio[BLANCO] + komi

    if total_negro > total_blanco:
        ganador = NEGRO
        margen = total_negro - total_blanco
    elif total_blanco > total_negro:
        ganador = BLANCO
        margen = total_blanco - total_negro
    else:
        ganador = None
        margen = 0.0

    return {
        "territorio": {NEGRO: territorio[NEGRO], BLANCO: territorio[BLANCO]},
        "piedras": piedras,
        "totales": {"negro": total_negro, "blanco": total_blanco},
        "komi": komi,
        "ganador": ganador,
        "margen": round(margen, 1),
    }


class Partida:
    """Partida de Go con turnos alternos, pases y resultado."""

    def __init__(self, tamano: int = 9, komi: float = 7.5, jugadores: dict | None = None):
        self.tablero = Tablero(tamano)
        self.komi = komi
        self.tamano = tamano
        self.turno = NEGRO
        self.terminada = False
        self.resultado = None
        self.pases_consecutivos = 0
        self.jugadores = jugadores or {NEGRO: None, BLANCO: None}
        self.movimientos = []
        self.registro = []
        self.rendicion = None

    def _cambiar_turno(self) -> None:
        self.turno = oponer(self.turno)

    def jugar(self, fila: int, col: int) -> dict:
        """Juega un movimiento del color al turno."""
        if self.terminada:
            raise ValueError("la partida ya terminó")
        color = self.turno
        info = self.tablero.colocar_piedra(fila, col, color)
        self.pases_consecutivos = 0
        self._cambiar_turno()
        self.movimientos.append((fila, col, color))
        self.registro.append({
            "tipo": "jugada",
            "coord": [fila, col],
            "color": color,
            "capturas": info["capturas"],
            "tiempo_ms": 0.0,
            "ai": None,
            "perf": None,
        })
        return info

    def pasar(self) -> None:
        """Registra un pase del color al turno."""
        if self.terminada:
            raise ValueError("la partida ya terminó")
        color = self.turno
        self.pases_consecutivos += 1
        self.movimientos.append((None, None, color))
        self.registro.append({
            "tipo": "pase",
            "coord": None,
            "color": color,
            "capturas": 0,
            "tiempo_ms": 0.0,
            "ai": None,
            "perf": None,
        })
        if self.pases_consecutivos >= 2:
            self.finalizar()
        else:
            self._cambiar_turno()

    def agregar_metadatos_ultimo_movimiento(self, datos: dict) -> None:
        """Fusiona métricas adicionales (IA, perf, temporización) al último movimiento."""
        if self.registro:
            self.registro[-1].update(datos)

    def rendirse(self, color: int = None) -> None:
        """El color dado (o el que está al turno) se rinde."""
        if self.terminada:
            raise ValueError("la partida ya terminó")
        perdedor = color or self.turno
        ganador = oponer(perdedor)
        self.rendicion = {"ganador": ganador, "perdedor": perdedor}
        self.resultado = {
            "ganador": ganador,
            "por_rendicion": True,
            "margen": None,
        }
        self.terminada = True

    def finalizar(self) -> dict:
        """Finaliza la partida y calcula el resultado por área."""
        puntaje = calcular_puntaje(self.tablero, self.komi)
        puntaje["por_rendicion"] = False
        puntaje["movimientos"] = len(self.movimientos)
        self.resultado = puntaje
        self.terminada = True
        return puntaje

    def obtener_movimientos_legales(self):
        return self.tablero.obtener_movimientos_legales(self.turno)

    def obtener_estado(self) -> dict:
        """Resumen del estado actual para la API y la interfaz."""
        return {
            "turno": self.turno,
            "terminada": self.terminada,
            "pases_consecutivos": self.pases_consecutivos,
            "tablero": self.tablero.obtener_estado(),
            "capturas": dict(self.tablero.capturas),
            "resultado": self.resultado,
            "num_movimientos": len(self.movimientos),
        }