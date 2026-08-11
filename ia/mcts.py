"""MCTS + UCT con playouts heurísticos."""

import math
import time

from motor import oponer
from .rollout import simular_partida

CLAVE_PASE = ("pase",)


class Nodo:
    """Nodo del árbol de búsqueda."""

    __slots__ = ("fila", "col", "padre", "hijos", "visitas", "q")

    def __init__(self, fila=None, col=None, padre=None):
        self.fila = fila
        self.col = col
        self.padre = padre
        self.hijos = {}
        self.visitas = 0
        self.q = 0.0

    def valor_uct(self, exploracion: float) -> float:
        """Valor UCT desde la perspectiva del jugador al turno del nodo."""
        if self.visitas == 0:
            return float("inf")
        if self.padre is None or self.padre.visitas == 0:
            return self.q / self.visitas
        return (self.q / self.visitas
                + exploracion * math.sqrt(math.log(self.padre.visitas) / self.visitas))

    def es_pase(self) -> bool:
        return self.fila is None and self.col is None

    def clave(self):
        return CLAVE_PASE if self.es_pase() else (self.fila, self.col)


class MCTS:
    """Búsqueda Monte Carlo con UCT para elegir la mejor jugada."""

    def __init__(self, simulaciones: int = 800, exploracion: float = 1.4,
                 tiempo_limite_ms: int | None = None, pliegues_rollout: int = 40):
        self.simulaciones = simulaciones
        self.exploracion = exploracion
        self.tiempo_limite_ms = tiempo_limite_ms
        self.pliegues_rollout = pliegues_rollout

    def _nombre_config(self) -> str:
        return f"mcts-{self.simulaciones}"

    @staticmethod
    def _tablero_saturado(partida) -> bool:
        """True si el tablero está casi lleno: momento natural de pasar."""
        tablero = partida.tablero
        ocupadas = 0
        total = tablero.tamano * tablero.tamano
        for fila in tablero.celdas:
            for celda in fila:
                if celda != 0:
                    ocupadas += 1
        return ocupadas / total >= 0.92

    def mejor_jugada(self, partida) -> dict:
        """Calcula la mejor jugada para el jugador al turno.

        Devuelve un dict con coordenadas (o pase), simulaciones y KPIs.
        """
        raiz, iteraciones, nodos_totales, tiempo_ms = self._buscar(partida)
        mejor = None
        mejor_visitas = -1
        for hijo in raiz.hijos.values():
            if hijo.visitas > mejor_visitas or (
                    hijo.visitas == mejor_visitas and mejor is not None
                    and hijo.q / max(1, hijo.visitas) > mejor.q / max(1, mejor.visitas)):
                mejor = hijo
                mejor_visitas = hijo.visitas

        # En tableros casi llenos ya no hay territorio útil: pasar para que la
        # partida termine por doble pase en lugar de rellenar a ciegas.
        if mejor is not None and self._tablero_saturado(partida):
            mejor = None

        es_pase = mejor is None or mejor.es_pase()
        win_rate = round(mejor.q / mejor.visitas, 4) if mejor and mejor.visitas else 0.0

        return {
            "fila": None if es_pase else mejor.fila,
            "col": None if es_pase else mejor.col,
            "pase": es_pase,
            "win_rate": win_rate,
            "sims": iteraciones,
            "nodes": nodos_totales,
            "tiempo_ms": round(tiempo_ms, 2),
            "exploracion": self.exploracion,
            "config": self._nombre_config(),
        }

    def analizar(self, partida, n: int = 5) -> dict:
        """Analiza la posición actual sin jugar: devuelve las n mejores jugadas.

        Cada opción incluye coordenadas (o pase), visitas, valor Q y win-rate
        desde la perspectiva del jugador al turno.
        """
        raiz, iteraciones, nodos_totales, tiempo_ms = self._buscar(partida)
        hijos = sorted(raiz.hijos.values(),
                       key=lambda h: (h.visitas, h.q / max(1, h.visitas)),
                       reverse=True)
        opciones = []
        for hijo in hijos[:n]:
            opciones.append({
                "fila": None if hijo.es_pase() else hijo.fila,
                "col": None if hijo.es_pase() else hijo.col,
                "pase": hijo.es_pase(),
                "visitas": hijo.visitas,
                "q": round(hijo.q, 4),
                "win_rate": round(hijo.q / max(1, hijo.visitas), 4),
            })
        return {
            "opciones": opciones,
            "sims": iteraciones,
            "nodes": nodos_totales,
            "tiempo_ms": round(tiempo_ms, 2),
            "exploracion": self.exploracion,
            "config": self._nombre_config(),
        }

    def _buscar(self, partida):
        """Ejecuta la búsqueda completa y devuelve raíz y KPIs agregados."""
        tablero = partida.tablero.copiar()
        color_inicial = partida.turno
        komi = partida.komi

        raiz = Nodo()
        inicio = time.perf_counter()
        iteraciones = 0
        nodos_totales = 1

        while iteraciones < self.simulaciones:
            if (self.tiempo_limite_ms is not None
                    and (time.perf_counter() - inicio) * 1000 > self.tiempo_limite_ms):
                break
            nodos_totales += self._iteracion(raiz, tablero, color_inicial, komi)
            iteraciones += 1

        tiempo_ms = (time.perf_counter() - inicio) * 1000
        return raiz, iteraciones, nodos_totales, tiempo_ms

    def _iteracion(self, raiz: Nodo, tablero_raiz, color_raiz: int, komi: float) -> int:
        """Una iteración: descenso, expansión perezosa y rollout en la primera hoja sin visitar."""
        tablero = tablero_raiz.copiar()
        color = color_raiz
        pases = 0
        nodo = raiz
        camino = [raiz]
        creados = 0

        while True:
            if nodo.visitas == 0:
                valor = self._evaluar(tablero, color, komi)
                self._retropropagar(camino, valor)
                return creados

            if not nodo.hijos:
                creados += self._expandir(nodo, tablero, color)

            hijo = self._seleccionar_hijo(nodo)
            camino.append(hijo)
            if hijo.es_pase():
                pases += 1
            else:
                pases = 0
                tablero.colocar_piedra(hijo.fila, hijo.col, color)
            color = oponer(color)
            nodo = hijo

            if pases >= 2:
                self._retropropagar(camino, self._evaluar(tablero, color, komi))
                return creados
            if not tablero.obtener_movimientos_legales(color):
                self._retropropagar(camino, self._evaluar(tablero, color, komi))
                return creados

    def _expandir(self, nodo: Nodo, tablero, color: int) -> int:
        movimientos = tablero.obtener_movimientos_legales(color)
        creados = 0
        for fila, col in movimientos:
            clave = (fila, col)
            if clave in nodo.hijos:
                continue
            nodo.hijos[clave] = Nodo(fila, col, padre=nodo)
            creados += 1
        if CLAVE_PASE not in nodo.hijos:
            nodo.hijos[CLAVE_PASE] = Nodo(padre=nodo)
            creados += 1
        return creados

    def _seleccionar_hijo(self, nodo: Nodo) -> Nodo:
        return max(nodo.hijos.values(), key=lambda h: h.valor_uct(self.exploracion))

    def _evaluar(self, tablero, color_movedor: int, komi: float) -> float:
        """Simula la posición: resultado 0..1."""
        ganador, _ = simular_partida(tablero, color_movedor, komi, self.pliegues_rollout)
        if ganador is None:
            return 0.5
        return 1.0 if ganador == color_movedor else 0.0

    def _retropropagar(self, camino: list, valor: float) -> None:
        valor_actual = valor
        for nodo in reversed(camino):
            nodo.visitas += 1
            nodo.q += valor_actual
            valor_actual = 1.0 - valor_actual


def crear_mcts(simulaciones: int = 800, tiempo_limite_ms: int | None = None) -> MCTS:
    """Factoría rápida para el MCTS heurístico."""
    return MCTS(simulaciones=simulaciones, tiempo_limite_ms=tiempo_limite_ms)