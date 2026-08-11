"""Pruebas para la inteligencia artificial de Go."""

import unittest

from motor_go import JuegoGo, VACIO
from ia_go import InteligenciaGo


class TestInteligenciaGo(unittest.TestCase):
    """Pruebas básicas para comprobar el funcionamiento de MCTS."""

    def setUp(self):

        # Usamos tablero 5x5 para que las pruebas sean rápidas.
        self.juego = JuegoGo(tamano=5)

        # Pocas simulaciones para no hacer lentos los tests.
        self.ia = InteligenciaGo(simulaciones=10)


    def test_ia_devuelve_movimiento(self):
        """La IA debe devolver una jugada."""

        movimiento = self.ia.seleccionar_movimiento(
            self.juego
        )

        self.assertIsNotNone(movimiento)


    def test_movimiento_ia_es_valido(self):
        """La jugada escogida por la IA debe ser legal."""

        movimiento = self.ia.seleccionar_movimiento(
            self.juego
        )

        fila, columna = movimiento

        self.assertTrue(
            self.juego.es_jugada_valida(
                fila,
                columna
            )
        )


    def test_ia_no_juega_en_casilla_ocupada(self):
        """La IA nunca debe escoger una posición ocupada."""

        # Negra ocupa el centro.
        self.juego.jugar(2, 2)

        movimiento = self.ia.seleccionar_movimiento(
            self.juego
        )

        self.assertNotEqual(
            movimiento,
            (2, 2)
        )


    def test_ia_no_modifica_tablero_al_pensar(self):
        """
        La búsqueda MCTS debe realizarse sobre copias.

        El tablero real no debe cambiar mientras
        la IA selecciona su movimiento.
        """

        tablero_antes = [
            fila[:]
            for fila in self.juego.tablero
        ]

        self.ia.seleccionar_movimiento(
            self.juego
        )

        self.assertEqual(
            self.juego.tablero,
            tablero_antes
        )


    def test_ia_puede_realizar_jugada(self):
        """La jugada seleccionada debe poder ejecutarse."""

        movimiento = self.ia.seleccionar_movimiento(
            self.juego
        )

        fila, columna = movimiento

        resultado = self.juego.jugar(
            fila,
            columna
        )

        self.assertTrue(resultado)

        self.assertNotEqual(
            self.juego.tablero[fila][columna],
            VACIO
        )


if __name__ == "__main__":
    unittest.main()