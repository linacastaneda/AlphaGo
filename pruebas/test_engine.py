"""Tests del motor de Go: capturas, suicidio, ko y puntuación."""

import pytest

from motor import NEGRO, BLANCO
from motor.board import Tablero
from motor.scoring import Partida


def test_es_dentro():
    t = Tablero(9)
    assert t.dentro(0, 0)
    assert t.dentro(8, 8)
    assert not t.dentro(9, 0)
    assert not t.dentro(-1, 4)


def test_ocupar_celda_ocupada():
    t = Tablero(9)
    t.colocar_piedra(4, 4, NEGRO)
    assert not t.es_movimiento_legal(4, 4, NEGRO)


def test_fuera_del_tablero():
    t = Tablero(9)
    assert not t.es_movimiento_legal(9, 9, NEGRO)


def test_captura_piedra_simple():
    """Una piedra negra rodeada por blancas es capturada."""
    t = Tablero(9)
    t.colocar_piedra(1, 0, NEGRO)
    t.colocar_piedra(1, 1, BLANCO)
    t.colocar_piedra(0, 0, BLANCO)
    # negro en (1,0) queda con una sola libertad: (2,0)
    assert t.capturas[BLANCO] == 0
    info = t.colocar_piedra(2, 0, BLANCO)
    assert info["capturas"] == 1
    assert t.celdas[1][0] == 0


def test_captura_directa():
    """Blanco captura una piedra negra solitaria."""
    t = Tablero(9)
    # negro en (0,1) con blancas en (0,0) y (1,1); única libertad: (0,2)
    t.colocar_piedra(0, 1, NEGRO)
    t.colocar_piedra(0, 0, BLANCO)
    t.colocar_piedra(1, 1, BLANCO)
    assert t.capturas[BLANCO] == 0
    # blanco juega (0,2) y captura el negro
    t.colocar_piedra(0, 2, BLANCO)
    assert t.capturas[BLANCO] == 1
    assert t.celdas[0][1] == 0


def test_captura_de_grupo_grande():
    """Se captura un grupo de varias piedras de una vez."""
    t = Tablero(9)
    # grupo negro de 2 piedras en (1,1) y (1,2), rodeado salvo por (2,2)
    t.colocar_piedra(1, 1, NEGRO)
    t.colocar_piedra(1, 2, NEGRO)
    t.colocar_piedra(0, 1, BLANCO)
    t.colocar_piedra(0, 2, BLANCO)
    t.colocar_piedra(1, 0, BLANCO)
    t.colocar_piedra(1, 3, BLANCO)
    t.colocar_piedra(2, 1, BLANCO)
    assert t.capturas[BLANCO] == 0
    t.colocar_piedra(2, 2, BLANCO)
    assert t.capturas[BLANCO] == 2


def test_suicidio_ilegal():
    """No se puede jugar en un punto sin libertades y sin capturar."""
    t = Tablero(9)
    # negro rodea (4,4) con 4 blancas
    t.colocar_piedra(3, 4, BLANCO)
    t.colocar_piedra(5, 4, BLANCO)
    t.colocar_piedra(4, 3, BLANCO)
    t.colocar_piedra(4, 5, BLANCO)
    with pytest.raises(ValueError, match="suicidio"):
        t.colocar_piedra(4, 4, NEGRO)


def test_suicidio_con_captura_permitido():
    """Jugar un punto sin libertades propias pero que captura es legal."""
    t = Tablero(9)
    # las cuatro vecinas de (4,4) son blancas solitarias, cada una en atari
    # con (4,4) como única libertad; el resto de sus vecinas son negras
    rodeos = [
        (2, 4), (3, 3), (3, 5),   # alrededor de blanco (3,4)
        (6, 4), (5, 3), (5, 5),   # alrededor de blanco (5,4)
        (4, 2),                   # faltante alrededor de blanco (4,3)
        (4, 6),                   # faltante alrededor de blanco (4,5)
    ]
    for fila, col in rodeos:
        t.colocar_piedra(fila, col, NEGRO)
    for fila, col in [(3, 4), (5, 4), (4, 3), (4, 5)]:
        t.colocar_piedra(fila, col, BLANCO)
    assert t.capturas[NEGRO] == 0
    # negro cae en un punto sin libertades propias, pero captura 4 piedras
    info = t.colocar_piedra(4, 4, NEGRO)
    assert info["capturas"] == 4
    assert t.capturas[NEGRO] == 4


def test_seki_vitalidad_basica():
    """Sekis básicos no capturan en ninguno de los dos lados."""
    t = Tablero(9)
    # esquema de seki mínimo: dos grupos con libertades compartidas
    t.colocar_piedra(0, 1, NEGRO)
    t.colocar_piedra(1, 0, BLANCO)
    assert t.capturas[NEGRO] == 0
    assert t.capturas[BLANCO] == 0


def test_ko_detectado_y_prohibido():
    """La recaptura inmediata del ko queda prohibida en la jugada siguiente."""
    t = Tablero(9)
    # posición de ko en el borde superior: negro captura la blanca de (0,0)
    t.colocar_piedra(1, 0, NEGRO)
    t.colocar_piedra(0, 0, BLANCO)
    t.colocar_piedra(0, 2, BLANCO)
    t.colocar_piedra(1, 1, BLANCO)
    info = t.colocar_piedra(0, 1, NEGRO)
    assert info["capturas"] == 1
    assert t.punto_ko == (0, 0)
    # blanco no puede recapturar en (0,0) inmediatamente (regla ko)
    assert not t.es_movimiento_legal(0, 0, BLANCO)


def test_doble_pase_finaliza_partida():
    p = Partida(9)
    p.jugar(0, 0)
    p.pasar()
    p.pasar()
    assert p.terminada
    assert p.resultado is not None
    assert p.resultado["ganador"] in (NEGRO, BLANCO)


def test_puntuacion_area_piedras_solo():
    """Sin territorio, puntúa por piedras (más komi)."""
    p = Partida(9, komi=7.5)
    celdas = [(f, c) for f in range(4) for c in range(4)]
    index = 0
    for fila, col in celdas:
        p.jugar(fila, col)
        index += 1
    p.pasar()
    p.pasar()
    assert p.terminada
    totales = p.resultado["totales"]
    # 8 piedras negras y 8 blancas llenan 4x4; blanco gana por komi
    assert totales["negro"] == 8
    assert totales["blanco"] == 15.5
    assert p.resultado["ganador"] == BLANCO


def test_rendicion():
    p = Partida(9)
    p.jugar(0, 0)
    p.rendirse(BLANCO)
    assert p.terminada
    assert p.resultado["ganador"] == NEGRO
    assert p.resultado["por_rendicion"]


def test_movimiento_tras_finalizar_lanza_error():
    p = Partida(9)
    p.pasar()
    p.pasar()
    with pytest.raises(ValueError, match="terminó"):
        p.jugar(0, 0)


def test_libertades_de_grupo():
    t = Tablero(9)
    t.colocar_piedra(4, 4, NEGRO)
    t.colocar_piedra(4, 5, NEGRO)
    grupo = t.obtener_grupo(4, 4)
    libs = t.calcular_libertades(grupo)
    assert len(grupo) == 2
    assert (3, 4) in libs
    assert (5, 5) in libs


def test_representacion_texto():
    t = Tablero(9)
    t.colocar_piedra(0, 0, NEGRO)
    assert "●" in repr(t)