"""Tests del generador de self-play SGF."""

from motor.scoring import Partida
from entrenamiento.dataset import parsear_sgf
from entrenamiento.self_play import generar_muchas, generar_sgf


def test_sgf_generado_es_valido_y_reprodu_cible():
    partida = generar_sgf(config_negro="aleatorio", config_blanco="aleatorio",
                          semilla=5)
    datos = parsear_sgf(partida["sgf"])
    assert datos["tamano"] == 9
    assert datos["resultado"].startswith(("B", "W", "0"))
    assert len(datos["movimientos"]) >= partida["num_movimientos"]

    # re-jugar la SGF con el motor: debe terminar con una partida consistente
    p = Partida(9, 7.5)
    n = 0
    for color, fila, col in datos["movimientos"]:
        if fila is None:
            p.pasar()
        else:
            p.jugar(fila, col)
        n += 1
    assert p.terminada is True
    if partida["ganador"] in (1, 2):
        assert p.resultado["ganador"] == partida["ganador"]


def test_generar_muchas_escribe_sgf(tmp_path):
    rutas = generar_muchas(partidas=3, config="aleatorio",
                           directorio=tmp_path, semilla_inicial=9)
    assert len(rutas) == 3
    for ruta in rutas:
        assert ruta.exists()
        texto = ruta.read_text(encoding="utf-8")
        assert texto.startswith("(;GM[1]FF[4]SZ[9]")