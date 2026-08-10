"""Módulo para representar y jugar una partida simple de Go."""

# Valores que utilizaremos para representar el tablero.
VACIO = 0
NEGRA = 1
BLANCA = -1


class JuegoGo:
    """Representa una partida de Go en un tablero cuadrado."""

    def __init__(self, tamano=9):
        """Inicializa una partida con un tablero vacío y el turno de las negras."""
        self.tamano = tamano
        self.tablero = [[VACIO for _ in range(tamano)] for _ in range(tamano)]
        self.jugador_actual = NEGRA
        self.tablero_anterior = None
        self.pases_consecutivos = 0

    def jugar(self, fila, columna):
        """Coloca una piedra del jugador actual si la jugada es válida.

        Args:
            fila (int): Índice de la fila donde se quiere jugar.
            columna (int): Índice de la columna donde se quiere jugar.

        Returns:
            bool: True si la jugada fue válida; False en caso contrario.
        """

        if not self.es_jugada_valida(fila, columna):
            return False
        
        self.tablero_anterior = [
                fila_tablero[:]
                for fila_tablero in self.tablero
            ]
         # Colocamos la piedra del jugador actual

        self.tablero[fila][columna] = self.jugador_actual

        self.revisar_capturas(fila, columna)

        # Como alguien jugó una piedra, se rompe la secuencia de pases
        self.pases_consecutivos = 0

         # Cambiamos el turno
        self.jugador_actual *= -1
        return True

    def mostrar_tablero(self):
        """Muestra el tablero actual en la consola con símbolos legibles."""

        for fila in self.tablero:
            for posicion in fila:
                if posicion == VACIO:
                    simbolo = "."
                elif posicion == NEGRA:
                    simbolo = "X"
                else:
                    simbolo = "O"
                print(simbolo, end=" ")
            print()
    def obtener_vecinos(self, fila, columna):
        """Obtiene las posiciones vecinas de una celda en el tablero."""

        vecinos = []

        # Arriba
        if fila > 0:
            vecinos.append((fila - 1, columna))

        # Abajo
        if fila < self.tamano - 1:
            vecinos.append((fila + 1, columna))

        # Izquierda
        if columna > 0:
            vecinos.append((fila, columna - 1))

        # Derecha
        if columna < self.tamano - 1:
            vecinos.append((fila, columna + 1))

        return vecinos
    
    def tiene_libertad(self, fila, columna):

        vecinos = self.obtener_vecinos(fila, columna) # Obtenemos los vecinos de la posición dada

        for fila_vecina, columna_vecina in vecinos: # Iteramos sobre cada vecino

            if self.tablero[fila_vecina][columna_vecina] == VACIO: # Si encontramos un vecino vacío, significa que la piedra tiene libertad
                return True

        return False
    
    def obtener_grupo(self, fila, columna):
        """Obtiene todas las piedras conectadas del mismo color a partir de una posición dada."""

        color = self.tablero[fila][columna]

        grupo = set()
        pendientes = [(fila, columna)]

        while pendientes:

            fila_actual, columna_actual = pendientes.pop()

            if (fila_actual, columna_actual) in grupo:
                continue

            grupo.add((fila_actual, columna_actual))

            vecinos = self.obtener_vecinos(
                fila_actual,
                columna_actual
            )

            for fila_vecina, columna_vecina in vecinos:

                if self.tablero[fila_vecina][columna_vecina] == color:

                    if (fila_vecina, columna_vecina) not in grupo:
                        pendientes.append(
                            (fila_vecina, columna_vecina)
                        )

        return grupo
    
    def obtener_libertades_grupo(self, grupo):

        libertades = set()

        for fila, columna in grupo:

            vecinos = self.obtener_vecinos(
                fila,
                columna
            )

            for fila_vecina, columna_vecina in vecinos:

                if self.tablero[fila_vecina][columna_vecina] == VACIO:

                    libertades.add(
                        (fila_vecina, columna_vecina)
                    )

        return libertades
    
    def eliminar_grupo(self, grupo):

        for fila, columna in grupo:
            self.tablero[fila][columna] = VACIO

    def revisar_capturas(self, fila, columna):

        jugador_enemigo = self.jugador_actual * -1

        vecinos = self.obtener_vecinos(fila, columna)

        for fila_vecina, columna_vecina in vecinos:

            if self.tablero[fila_vecina][columna_vecina] == jugador_enemigo:

                grupo_enemigo = self.obtener_grupo(
                    fila_vecina,
                    columna_vecina
                )

                libertades = self.obtener_libertades_grupo(
                    grupo_enemigo
                )

                if len(libertades) == 0:
                    self.eliminar_grupo(grupo_enemigo)

    def es_jugada_valida(self, fila, columna):

        if fila < 0 or fila >= self.tamano:
            return False

        if columna < 0 or columna >= self.tamano:
            return False

        if self.tablero[fila][columna] != VACIO:
            return False

        tablero_actual = [
            fila_tablero[:]
            for fila_tablero in self.tablero
        ]

        self.tablero[fila][columna] = self.jugador_actual

        self.revisar_capturas(fila, columna)

        grupo = self.obtener_grupo(fila, columna)

        libertades = self.obtener_libertades_grupo(grupo)

        if len(libertades) == 0:

            self.tablero = tablero_actual

            return False

        if self.tablero_anterior is not None:

            if self.tablero == self.tablero_anterior:

                self.tablero = tablero_actual

                return False

        self.tablero = tablero_actual

        return True

    def pasar_turno(self):
        """Permite que el jugador actual pase su turno."""

        self.pases_consecutivos += 1

        self.jugador_actual *= -1

        return True
    def partida_terminada(self):
        """Indica si ambos jugadores pasaron consecutivamente."""

        return self.pases_consecutivos >= 2
