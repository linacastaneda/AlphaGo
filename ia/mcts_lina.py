"""MCTS de Lina portado a nuestro motor.

Versión académica (UCT clásico + rollout aleatorio puro) que usa
``engine`` en lugar de ``backend.motor_go``:

- Expande un solo hijo aleatorio por iteración (no expansión perezosa).
- Selección con UCT (constante de exploración 1.414, clásica de √2).
- Simulación con movimientos aleatorios + 5% de pases voluntarios.
- Decisión final: hijo con más visitas.
- Respeta ``tiempo_limite_ms`` de forma nativa en el bucle (sin calibración),
  por lo que es mucho más rápido que el adaptador anterior.

Al ser autónomo, se puede jugar sin importar nada de ``backend/``.
"""

import math
import random
import time

from motor import NEGRO, BLANCO, oponer


class NodoMCTS:
    """Nodo del árbol: estadísticas y movimientos pendientes de explorar.

    ``movimiento`` es ``(fila, col)`` o ``None`` (pase).
    """

    __slots__ = ("padre", "movimiento", "jugador_que_movio", "hijos",
                 "visitas", "victorias", "movimientos_no_explorados")

    def __init__(self, padre=None, movimiento=None, jugador_que_movio=None,
                 movimientos_validos=None):
        self.padre = padre
        self.movimiento = movimiento
        self.jugador_que_movio = jugador_que_movio
        self.hijos = []
        self.visitas = 0
        self.victorias = 0.0
        if movimientos_validos is not None:
            self.movimientos_no_explorados = list(movimientos_validos)
            self.movimientos_no_explorados.append(None)  # pasar turno
        else:
            self.movimientos_no_explorados = []

    def esta_totalmente_expandido(self):
        return len(self.movimientos_no_explorados) == 0

    def seleccionar_mejor_hijo(self, constante_exploracion=1.414):
        mejor_hijo = None
        mejor_valor = float("-inf")
        for hijo in self.hijos:
            if hijo.visitas == 0:
                return hijo
            explotacion = hijo.victorias / hijo.visitas
            exploracion = (constante_exploracion
                           * math.sqrt(math.log(max(1, self.visitas)) / hijo.visitas))
            valor_uct = explotacion + exploracion
            if valor_uct > mejor_valor:
                mejor_valor = valor_uct
                mejor_hijo = hijo
        return mejor_hijo


class _Estado:
    """Estado ligero para simulación: tablero + turno + pases consecutivos.

    Evita la copia del objeto ``Partida`` completo (registro, metadatos…).
    """

    __slots__ = ("tablero", "turno", "pases")

    def __init__(self, tablero, turno, pases=0):
        self.tablero = tablero
        self.turno = turno
        self.pases = pases

    def copiar(self):
        return _Estado(self.tablero.copiar(), self.turno, self.pases)

    def movimientos_validos(self):
        return self.tablero.obtener_movimientos_legales(self.turno)

    def terminar_turno(self):
        self.turno = oponer(self.turno)

    def jugar(self, fila, col):
        self.tablero.colocar_piedra(fila, col, self.turno)
        self.pases = 0
        self.terminar_turno()

    def pasar_turno(self):
        self.pases += 1
        self.terminar_turno()

    def partida_terminada(self):
        return self.pases >= 2


class MCTSLina:
    """Búsqueda Monte Carlo con UCT (estilo académico) sobre nuestro motor."""

    def __init__(self, simulaciones: int = 100, tiempo_limite_ms: int | None = None,
                 constante_exploracion: float = 1.414, pliegues_rollout: int | None = None):
        self.simulaciones = simulaciones
        self.tiempo_limite_ms = tiempo_limite_ms
        self.constante_exploracion = constante_exploracion
        self.pliegues_rollout = pliegues_rollout

    def _limite_rollout(self, tamano: int) -> int:
        """Máximo de movimientos simulados por rollout.

        El valor clásico es ``tamano * tamano * 2`` (juego completo), pero es
        mucho más lento. Por defecto usamos ``tamano * tamano``: mantiene el
        rollout largo (suficiente para evaluar territorio) a una fracción
        del coste. Se puede restaurar el original con ``pliegues_rollout``.
        """
        if self.pliegues_rollout is not None:
            return self.pliegues_rollout
        return tamano * tamano

    def _nombre_config(self) -> str:
        return f"mcts-l-{self.simulaciones}"

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
        return ocupadas / total >= 0.85

    def mejor_jugada(self, partida) -> dict:
        inicio = time.perf_counter()
        decision, iteraciones, nodos = self._buscar(partida)
        if decision is not None and self._tablero_saturado(partida):
            decision = None
        tiempo_ms = (time.perf_counter() - inicio) * 1000
        es_pase = decision is None
        return {
            "fila": None if es_pase else decision[0],
            "col": None if es_pase else decision[1],
            "pase": es_pase,
            "win_rate": 0.0,
            "sims": iteraciones,
            "nodes": nodos,
            "tiempo_ms": round(tiempo_ms, 2),
            "exploracion": self.constante_exploracion,
            "config": self._nombre_config(),
        }

    def analizar(self, partida, n: int = 5) -> dict:
        # Conserva la interfaz de MCTS; no expone el árbol completo.
        inicio = time.perf_counter()
        decision, iteraciones, nodos = self._buscar(partida)
        opciones = []
        if decision is not None:
            opciones.append({
                "fila": decision[0], "col": decision[1], "pase": False,
                "visitas": iteraciones, "q": 0.0, "win_rate": 0.0,
            })
        return {
            "opciones": opciones,
            "sims": iteraciones,
            "nodes": nodos,
            "tiempo_ms": round((time.perf_counter() - inicio) * 1000, 2),
            "exploracion": self.constante_exploracion,
            "config": self._nombre_config(),
        }

    # ------------------------------------------------------------------
    # Búsqueda
    # ------------------------------------------------------------------

    def _buscar(self, partida):
        """Ejecuta MCTS sobre la partida y devuelve (movimiento, sims, nodos)."""
        raiz = NodoMCTS(
            jugador_que_movio=oponer(partida.turno),
            movimientos_validos=partida.obtener_movimientos_legales(),
        )
        if not raiz.movimientos_no_explorados:
            return None, 0, 1

        tablero_raiz = partida.tablero
        color_raiz = partida.turno
        komi = partida.komi
        tamano = partida.tamano
        limite_rollout = self._limite_rollout(tamano)

        inicio = time.perf_counter()
        iteraciones = 0
        nodos_totales = 1

        while iteraciones < self.simulaciones:
            if (self.tiempo_limite_ms is not None
                    and (time.perf_counter() - inicio) * 1000 > self.tiempo_limite_ms):
                break

            estado = _Estado(tablero_raiz.copiar(), color_raiz)
            nodo = raiz
            camino = [raiz]
            creados = 0

            # 1. SELECCIÓN
            while (nodo.esta_totalmente_expandido()
                   and nodo.hijos
                   and not estado.partida_terminada()):
                nodo = nodo.seleccionar_mejor_hijo(self.constante_exploracion)
                camino.append(nodo)
                self._aplicar(estado, nodo.movimiento)

            # 2. EXPANSIÓN
            if (not estado.partida_terminada()
                    and nodo.movimientos_no_explorados):
                movimiento = random.choice(nodo.movimientos_no_explorados)
                nodo.movimientos_no_explorados.remove(movimiento)
                jugador_actual = estado.turno
                if self._aplicar(estado, movimiento):
                    movimientos_hijo = estado.movimientos_validos()
                    hijo = NodoMCTS(
                        padre=nodo, movimiento=movimiento,
                        jugador_que_movio=jugador_actual,
                        movimientos_validos=movimientos_hijo)
                    nodo.hijos.append(hijo)
                    camino.append(hijo)
                    nodo = hijo
                    creados += 1
                    nodos_totales += 1

            # 3. SIMULACIÓN + 4. RETROPROPAGACIÓN
            ganador = self._simular_partida(estado, limite_rollout, komi)
            self._retropropagar(nodo, ganador)
            iteraciones += 1

        if not raiz.hijos:
            return None, iteraciones, nodos_totales
        mejor_hijo = max(raiz.hijos, key=lambda hijo: hijo.visitas)
        return mejor_hijo.movimiento, iteraciones, nodos_totales

    def _aplicar(self, estado: _Estado, movimiento) -> bool:
        """Aplica un movimiento: None es pase. Devuelve True si fue legal."""
        if movimiento is None:
            estado.pasar_turno()
            return True
        fila, col = movimiento
        if not estado.tablero.es_movimiento_legal(fila, col, estado.turno):
            return False
        estado.jugar(fila, col)
        return True

    def _simular_partida(self, estado: _Estado, limite_movimientos: int, komi: float):
        """Rollout aleatorio puro (5% de pases voluntarios) + conteo por área."""
        estado = estado.copiar()
        movimientos_realizados = 0
        while (not estado.partida_terminada()
               and movimientos_realizados < limite_movimientos):
            movimientos = estado.movimientos_validos()
            if not movimientos:
                estado.pasar_turno()
            elif random.random() < 0.05:
                estado.pasar_turno()
            else:
                fila, col = random.choice(movimientos)
                estado.jugar(fila, col)
            movimientos_realizados += 1

        from motor.scoring import calcular_puntaje
        return calcular_puntaje(estado.tablero, komi)["ganador"]

    def _retropropagar(self, nodo: NodoMCTS, ganador) -> None:
        while nodo is not None:
            nodo.visitas += 1
            if (nodo.jugador_que_movio is not None
                    and ganador == nodo.jugador_que_movio):
                nodo.victorias += 1.0
            elif ganador is None:
                nodo.victorias += 0.5
            nodo = nodo.padre


def crear_lina(simulaciones: int = 100, tiempo_limite_ms: int | None = None,
               constante_exploracion: float = 1.414) -> MCTSLina:
    """Factoría del MCTS estilo Lina."""
    return MCTSLina(simulaciones=simulaciones,
                    tiempo_limite_ms=tiempo_limite_ms,
                    constante_exploracion=constante_exploracion)
