"""MCTS + UCT con playouts heurísticos, preparado para priorizar con redes."""

import math
import random
import time

from engine import VACIO, oponer
from .rollout import simular_partida

CLAVE_PASE = ("pase",)


class Nodo:
    """Nodo del árbol de búsqueda."""

    __slots__ = ("fila", "col", "padre", "hijos", "visitas", "q", "prior")

    def __init__(self, fila=None, col=None, padre=None, prior=0.0):
        self.fila = fila
        self.col = col
        self.padre = padre
        self.hijos = {}
        self.visitas = 0
        self.q = 0.0
        self.prior = prior

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
                 tiempo_limite_ms: int | None = None, pliegues_rollout: int = 40,
                 redes=None):
        self.simulaciones = simulaciones
        self.exploracion = exploracion
        self.tiempo_limite_ms = tiempo_limite_ms
        self.pliegues_rollout = pliegues_rollout
        self.redes = redes

    def _nombre_config(self) -> str:
        return f"mcts-{self.simulaciones}" + ("+red" if self.redes is not None else "")

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
        priors = None
        if self.redes is not None:
            _, priors = self.redes.distribucion_politica(tablero, color)
        creados = 0
        for fila, col in movimientos:
            clave = (fila, col)
            if clave in nodo.hijos:
                continue
            prior = priors.get(clave, 0.0) if priors else 0.0
            nodo.hijos[clave] = Nodo(fila, col, padre=nodo, prior=prior)
            creados += 1
        if CLAVE_PASE not in nodo.hijos:
            prior_pase = priors.get(CLAVE_PASE, 0.0) if priors else 0.0
            nodo.hijos[CLAVE_PASE] = Nodo(padre=nodo, prior=prior_pase)
            creados += 1
        return creados

    def _seleccionar_hijo(self, nodo: Nodo) -> Nodo:
        if self.redes is None:
            return max(nodo.hijos.values(), key=lambda h: h.valor_uct(self.exploracion))

        def _puct(hijo: Nodo) -> float:
            if hijo.visitas == 0:
                return float("inf")
            q = hijo.q / hijo.visitas
            return q + self.exploracion * hijo.prior * math.sqrt(
                max(1, nodo.visitas)) / (1 + hijo.visitas)

        return max(nodo.hijos.values(), key=_puct)

    def _evaluar(self, tablero, color_movedor: int, komi: float) -> float:
        """Simula (o evalúa con red de valor) la posición: resultado 0..1."""
        if self.redes is not None:
            return self.redes.estimar_valor(tablero, color_movedor)
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


_redes_cargadas = None
_redes_intentado = False


def crear_mcts(simulaciones: int = 800, tiempo_limite_ms: int | None = None) -> MCTS:
    """Factoría rápida para el MCTS, guiada por redes si hay modelos disponibles."""
    global _redes_cargadas, _redes_intentado
    if not _redes_intentado:
        _redes_intentado = True
        try:
            from .redes import cargar_redes
            _redes_cargadas = cargar_redes()
        except Exception:
            _redes_cargadas = None
    return MCTS(simulaciones=simulaciones, tiempo_limite_ms=tiempo_limite_ms,
                redes=_redes_cargadas)