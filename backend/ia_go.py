"""
Inteligencia artificial para jugar Go mediante
Monte Carlo Tree Search (MCTS).

MCTS analiza diferentes movimientos mediante cuatro etapas:

1. Selección
2. Expansión
3. Simulación
4. Retropropagación

Esta implementación es una versión académica simplificada.
AlphaGo utilizaba además redes neuronales de política y valor
para orientar la búsqueda.
"""

import math
import random

from motor_go import NEGRA, BLANCA


class NodoMCTS:
    """
    Representa un nodo del árbol de búsqueda.

    El nodo NO almacena una copia completa del tablero.
    Solamente almacena información estadística y el movimiento
    realizado para llegar hasta él.
    """

    def __init__(
        self,
        padre=None,
        movimiento=None,
        jugador_que_movio=None,
        movimientos_validos=None
    ):

        # Nodo anterior dentro del árbol.
        self.padre = padre

        # Movimiento utilizado para llegar a este nodo.
        # None significa pasar turno.
        self.movimiento = movimiento

        # Jugador que realizó el movimiento que produjo este nodo.
        self.jugador_que_movio = jugador_que_movio

        # Nodos que salen desde este estado.
        self.hijos = []

        # Número de veces que el nodo ha sido visitado.
        self.visitas = 0

        # Número de resultados favorables para
        # jugador_que_movio.
        self.victorias = 0.0

        # Movimientos que todavía no han sido explorados.
        if movimientos_validos is not None:

            self.movimientos_no_explorados = list(
                movimientos_validos
            )

            # También se puede pasar turno.
            self.movimientos_no_explorados.append(None)

        else:

            self.movimientos_no_explorados = []


    def esta_totalmente_expandido(self):
        """
        Indica si todos los movimientos posibles desde
        este nodo ya fueron explorados.
        """

        return len(self.movimientos_no_explorados) == 0


    def seleccionar_mejor_hijo(
        self,
        constante_exploracion=1.414
    ):
        """
        Selecciona el hijo más prometedor mediante UCT.

        UCT combina:

        Explotación:
            Qué tan buenos han sido los resultados
            obtenidos por ese movimiento.

        Exploración:
            Qué tan poco se ha estudiado ese movimiento.
        """

        mejor_hijo = None
        mejor_valor = float("-inf")

        for hijo in self.hijos:

            # Si nunca hemos visitado este nodo,
            # debemos explorarlo.
            if hijo.visitas == 0:
                return hijo

            # Parte de explotación:
            # porcentaje de resultados favorables.
            explotacion = (
                hijo.victorias
                / hijo.visitas
            )

            # Parte de exploración.
            exploracion = (
                constante_exploracion
                * math.sqrt(
                    math.log(max(1, self.visitas))
                    / hijo.visitas
                )
            )

            # Fórmula UCT.
            valor_uct = (
                explotacion
                + exploracion
            )

            if valor_uct > mejor_valor:

                mejor_valor = valor_uct
                mejor_hijo = hijo

        return mejor_hijo


class InteligenciaGo:
    """
    Inteligencia artificial para jugar Go utilizando MCTS.
    """

    def __init__(self, simulaciones=100):
        """
        Args:
            simulaciones:
                Cantidad de iteraciones MCTS realizadas
                antes de seleccionar una jugada.

        Un número mayor permite estudiar más alternativas,
        pero aumenta el tiempo de respuesta.
        """

        self.simulaciones = simulaciones


    def seleccionar_movimiento(self, juego):
        """
        Ejecuta MCTS y devuelve la jugada seleccionada.

        Returns:
            (fila, columna) si decide colocar una piedra.

            None si decide pasar.
        """

        # No se puede jugar después de finalizar la partida.
        if juego.partida_terminada():
            return None

        movimientos = (
            juego.obtener_movimientos_validos()
        )

        # Si no hay movimientos disponibles,
        # se pasa automáticamente.
        if not movimientos:
            return None

        # --------------------------------------------------
        # CREACIÓN DE LA RAÍZ
        # --------------------------------------------------

        # La raíz representa la situación ANTES
        # de que juegue el jugador actual.
        #
        # Por eso indicamos que el jugador que realizó
        # el movimiento anterior fue el rival.
        jugador_anterior = (
            BLANCA
            if juego.jugador_actual == NEGRA
            else NEGRA
        )

        raiz = NodoMCTS(
            jugador_que_movio=jugador_anterior,
            movimientos_validos=movimientos
        )

        # --------------------------------------------------
        # ITERACIONES DE MONTE CARLO
        # --------------------------------------------------

        for _ in range(self.simulaciones):

            nodo = raiz

            # Solamente mantenemos UNA copia del juego
            # durante cada recorrido del árbol.
            estado = juego.copiar()

            # ==================================================
            # 1. SELECCIÓN
            # ==================================================

            # Recorremos nodos ya explorados utilizando UCT.
            while (
                nodo.esta_totalmente_expandido()
                and nodo.hijos
                and not estado.partida_terminada()
            ):

                nodo = (
                    nodo.seleccionar_mejor_hijo()
                )

                # Reproducimos sobre el estado local
                # el movimiento correspondiente.
                self._aplicar_movimiento(
                    estado,
                    nodo.movimiento
                )

            # ==================================================
            # 2. EXPANSIÓN
            # ==================================================

            if (
                not estado.partida_terminada()
                and nodo.movimientos_no_explorados
            ):

                # Elegimos aleatoriamente uno de los
                # movimientos todavía no estudiados.
                movimiento = random.choice(
                    nodo.movimientos_no_explorados
                )

                nodo.movimientos_no_explorados.remove(
                    movimiento
                )

                # Guardamos quién realiza la jugada.
                jugador_actual = (
                    estado.jugador_actual
                )

                # Aplicamos el movimiento.
                movimiento_realizado = (
                    self._aplicar_movimiento(
                        estado,
                        movimiento
                    )
                )

                if movimiento_realizado:

                    # Calculamos qué movimientos estarán
                    # disponibles desde el nuevo estado.
                    movimientos_hijo = (
                        estado.obtener_movimientos_validos()
                    )

                    hijo = NodoMCTS(
                        padre=nodo,
                        movimiento=movimiento,
                        jugador_que_movio=jugador_actual,
                        movimientos_validos=movimientos_hijo
                    )

                    nodo.hijos.append(hijo)

                    nodo = hijo
                else:
                    # Si el motor rechazó el movimiento (p. ej. regla de Ko o jugada ilegal),
                    # no avanzamos el nodo para no corromper la simulación.
                    pass

            # ==================================================
            # 3. SIMULACIÓN
            # ==================================================

            ganador = self._simular_partida(
                estado
            )

            # ==================================================
            # 4. RETROPROPAGACIÓN
            # ==================================================

            self._retropropagar(
                nodo,
                ganador
            )

        # --------------------------------------------------
        # DECISIÓN FINAL
        # --------------------------------------------------

        if not raiz.hijos:
            return None

        # Elegimos el nodo que fue explorado más veces.
        #
        # Esta es una estrategia habitual para obtener
        # la decisión final después de las simulaciones.
        mejor_hijo = max(
            raiz.hijos,
            key=lambda hijo: hijo.visitas
        )

        return mejor_hijo.movimiento


    def _aplicar_movimiento(
        self,
        juego,
        movimiento
    ):
        """
        Aplica un movimiento sobre una simulación.

        None representa pasar turno.
        """

        if movimiento is None:

            juego.pasar_turno()

            return True

        fila, columna = movimiento

        return juego.jugar(
            fila,
            columna
        )


    def _simular_partida(self, juego):
        """
        Realiza una simulación aleatoria desde el estado recibido.

        Esta fase también se conoce como rollout.
        """

        estado = juego.copiar()

        # Evitamos simulaciones excesivamente largas.
        #
        # En 9x9:
        # 9 × 9 × 2 = máximo 162 movimientos simulados.
        limite_movimientos = (
            estado.tamano
            * estado.tamano
            * 2
        )

        movimientos_realizados = 0

        while (
            not estado.partida_terminada()
            and movimientos_realizados
            < limite_movimientos
        ):

            movimientos = (
                estado.obtener_movimientos_validos()
            )

            # Si no existen movimientos legales,
            # el jugador pasa.
            if not movimientos:

                estado.pasar_turno()

            else:

                # Pequeña probabilidad de pasar voluntariamente.
                #
                # Esto permite que las simulaciones
                # puedan finalizar naturalmente.
                if random.random() < 0.05:

                    estado.pasar_turno()

                else:

                    movimiento = random.choice(
                        movimientos
                    )

                    estado.jugar(
                        movimiento[0],
                        movimiento[1]
                    )

            movimientos_realizados += 1

        # Si la partida terminó por dos pases,
        # o si alcanzamos el límite establecido,
        # evaluamos la posición mediante puntuación.
        puntos_negras, puntos_blancas = (
            estado.calcular_puntuacion()
        )

        if puntos_negras > puntos_blancas:
            return NEGRA

        if puntos_blancas > puntos_negras:
            return BLANCA

        # Empate.
        return 0


    def _retropropagar(
        self,
        nodo,
        ganador
    ):
        """
        Propaga el resultado de la simulación hacia la raíz.

        Cada nodo evalúa el resultado desde la perspectiva
        del jugador que realizó el movimiento que llevó
        hasta ese nodo.
        """

        while nodo is not None:

            nodo.visitas += 1

            # Victoria para el jugador que produjo
            # este estado.
            if (
                nodo.jugador_que_movio is not None
                and ganador
                == nodo.jugador_que_movio
            ):

                nodo.victorias += 1.0

            # Un empate vale medio punto.
            elif ganador == 0:

                nodo.victorias += 0.5

            # Subimos al nodo anterior.
            nodo = nodo.padre