"""Pruebas unitarias para el motor del juego de Go."""

import unittest

from motor_go import JuegoGo, VACIO, NEGRA, BLANCA


class TestJuegoGo(unittest.TestCase):
    """Pruebas unitarias para comprobar el funcionamiento de JuegoGo."""

    def setUp(self):
        """
        Se ejecuta antes de cada prueba.

        De esta manera, cada test comienza con una partida nueva
        y un tablero vacío de 5x5.
        """
        self.juego = JuegoGo(tamano=5)

    # ---------------------------------------------------------
    # 1. PRUEBAS DE INICIALIZACIÓN Y FUNCIONAMIENTO BÁSICO
    # ---------------------------------------------------------

    def test_inicializacion_tablero(self):
        """Verifica que el tablero empiece vacío y jueguen primero las negras."""

        self.assertEqual(self.juego.tamano, 5)
        self.assertEqual(self.juego.jugador_actual, NEGRA)

        # Todas las posiciones deben comenzar vacías.
        for fila in self.juego.tablero:
            for casilla in fila:
                self.assertEqual(casilla, VACIO)

    def test_movimiento_valido_y_cambio_turno(self):
        """Verifica la colocación de piedras y el cambio de turno."""

        # Juegan las negras.
        resultado = self.juego.jugar(2, 2)

        self.assertTrue(resultado)
        self.assertEqual(self.juego.tablero[2][2], NEGRA)

        # Después de jugar negras, debe ser el turno de blancas.
        self.assertEqual(self.juego.jugador_actual, BLANCA)

        # Juegan las blancas.
        resultado = self.juego.jugar(1, 1)

        self.assertTrue(resultado)
        self.assertEqual(self.juego.tablero[1][1], BLANCA)

        # Debe volver el turno a negras.
        self.assertEqual(self.juego.jugador_actual, NEGRA)

    def test_movimiento_fuera_de_limites(self):
        """Verifica que no se pueda jugar fuera del tablero."""

        self.assertFalse(self.juego.jugar(-1, 0))
        self.assertFalse(self.juego.jugar(0, -1))
        self.assertFalse(self.juego.jugar(0, 5))
        self.assertFalse(self.juego.jugar(5, 0))
        self.assertFalse(self.juego.jugar(5, 5))

    def test_casilla_ocupada(self):
        """Verifica que no se pueda jugar sobre una piedra existente."""

        # Negra ocupa (2, 2).
        self.assertTrue(self.juego.jugar(2, 2))

        # Blanca intenta jugar exactamente en la misma posición.
        resultado = self.juego.jugar(2, 2)

        self.assertFalse(resultado)

        # La piedra original debe seguir siendo negra.
        self.assertEqual(self.juego.tablero[2][2], NEGRA)

        # Como la jugada blanca fue inválida,
        # el turno debe continuar siendo de blancas.
        self.assertEqual(self.juego.jugador_actual, BLANCA)

    # ---------------------------------------------------------
    # 2. PRUEBAS DE VECINOS, GRUPOS Y LIBERTADES
    # ---------------------------------------------------------

    def test_obtener_vecinos_esquina(self):
        """Verifica los vecinos de una posición ubicada en una esquina."""

        vecinos = self.juego.obtener_vecinos(0, 0)

        self.assertEqual(
            set(vecinos),
            {(0, 1), (1, 0)}
        )

    def test_obtener_vecinos_centro(self):
        """Verifica los cuatro vecinos de una posición central."""

        vecinos = self.juego.obtener_vecinos(2, 2)

        self.assertEqual(
            set(vecinos),
            {
                (1, 2),
                (3, 2),
                (2, 1),
                (2, 3)
            }
        )

    def test_piedra_tiene_libertad(self):
        """Verifica que una piedra con espacios vacíos tenga libertad."""

        self.juego.jugar(2, 2)

        resultado = self.juego.tiene_libertad(2, 2)

        self.assertTrue(resultado)

    def test_grupo_de_piedras(self):
        """Verifica que dos piedras conectadas formen un mismo grupo."""

        self.juego.jugar(1, 1)  # Negra
        self.juego.jugar(4, 4)  # Blanca
        self.juego.jugar(1, 2)  # Negra

        grupo = self.juego.obtener_grupo(1, 1)

        self.assertEqual(
            grupo,
            {(1, 1), (1, 2)}
        )

    def test_libertades_de_grupo(self):
        """Verifica las libertades de dos piedras conectadas."""

        self.juego.jugar(1, 1)  # Negra
        self.juego.jugar(4, 4)  # Blanca
        self.juego.jugar(1, 2)  # Negra

        grupo = self.juego.obtener_grupo(1, 1)

        libertades = self.juego.obtener_libertades_grupo(grupo)

        # Dos piedras horizontales ubicadas en esta posición
        # tienen seis libertades.
        self.assertEqual(len(libertades), 6)

    # ---------------------------------------------------------
    # 3. PRUEBAS DE CAPTURA
    # ---------------------------------------------------------

    def test_captura_piedra_enemiga(self):
        """Verifica que una piedra sin libertades sea capturada."""

        # Negra que posteriormente será capturada.
        self.juego.jugar(1, 1)  # Negra

        # Primera piedra blanca alrededor.
        self.juego.jugar(0, 1)  # Blanca

        # Jugada negra de relleno.
        self.juego.jugar(4, 4)  # Negra

        # Segunda piedra blanca.
        self.juego.jugar(1, 0)  # Blanca

        # Jugada negra de relleno.
        self.juego.jugar(4, 3)  # Negra

        # Tercera piedra blanca.
        self.juego.jugar(1, 2)  # Blanca

        # Jugada negra de relleno.
        self.juego.jugar(3, 4)  # Negra

        # Blanca completa el cerco.
        self.juego.jugar(2, 1)  # Blanca

        # La piedra negra de (1, 1) debe desaparecer.
        self.assertEqual(
            self.juego.tablero[1][1],
            VACIO
        )

    # ---------------------------------------------------------
    # 4. PRUEBA DE LA REGLA DE SUICIDIO
    # ---------------------------------------------------------

    def test_regla_de_no_suicidio(self):
        """Verifica que una piedra no pueda jugarse sin libertades."""

        # Creamos cuatro piedras blancas alrededor de (1, 1).

        self.juego.jugar(4, 4)  # Negra
        self.juego.jugar(0, 1)  # Blanca

        self.juego.jugar(4, 3)  # Negra
        self.juego.jugar(1, 0)  # Blanca

        self.juego.jugar(3, 4)  # Negra
        self.juego.jugar(1, 2)  # Blanca

        self.juego.jugar(3, 3)  # Negra
        self.juego.jugar(2, 1)  # Blanca

        # Ahora es turno de negras.
        #
        # La posición (1, 1) está completamente rodeada:
        #
        # . O .
        # O . O
        # . O .
        #
        # Una piedra negra allí no tendría ninguna libertad.

        resultado = self.juego.jugar(1, 1)

        self.assertFalse(resultado)

        # Además de rechazar la jugada,
        # la posición debe permanecer vacía.
        self.assertEqual(
            self.juego.tablero[1][1],
            VACIO
        )

        # Una jugada inválida tampoco debe cambiar el turno.
        self.assertEqual(
            self.juego.jugador_actual,
            NEGRA
        )
    # ---------------------------------------------------------
    # 5. PRUEBA DE LA REGLA DEL KO
    # ---------------------------------------------------------

    def test_regla_del_ko(self):
        """Verifica que no se permita la recaptura inmediata que repita el tablero."""

        # Configuramos la posición inicial para un Ko clásico en (2, 1) y (1, 1):
        self.juego.jugar(2, 2)  # Negra
        self.juego.jugar(1, 2)  # Blanca
        self.juego.jugar(3, 1)  # Negra
        self.juego.jugar(2, 1)  # Blanca
        self.juego.jugar(2, 0)  # Negra
        self.juego.jugar(2, 3)  # Blanca

        # 1. Negra captura la piedra blanca de (2, 1) jugando en (1, 1).
        resultado_captura = self.juego.jugar(1, 1)
        self.assertTrue(resultado_captura)
        self.assertEqual(self.juego.tablero[2][1], VACIO)

        # 2. Ahora es turno de Blanca.
        # Blanca intenta recapturar la piedra en (2, 1) de inmediato.
        # Esto dejaría el tablero idéntico al estado de hace un turno,
        # por lo que debe ser prohibido por la regla del Ko.
        resultado_ko = self.juego.jugar(2, 1)

        self.assertFalse(resultado_ko)
        self.assertEqual(self.juego.tablero[2][1], VACIO)
        self.assertEqual(self.juego.jugador_actual, BLANCA)
    def test_pasar_turno(self):
        """Verifica que pasar cambie el turno y aumente el contador."""

        self.assertEqual(self.juego.jugador_actual, NEGRA)

        self.juego.pasar_turno()

        self.assertEqual(self.juego.jugador_actual, BLANCA)
        self.assertEqual(self.juego.pases_consecutivos, 1)


    def test_fin_partida_por_dos_pases(self):
        """Verifica que dos pases consecutivos terminen la partida."""

        self.assertFalse(self.juego.partida_terminada())

        self.juego.pasar_turno()

        self.assertFalse(self.juego.partida_terminada())

        self.juego.pasar_turno()

        self.assertTrue(self.juego.partida_terminada())


if __name__ == "__main__":
    unittest.main()