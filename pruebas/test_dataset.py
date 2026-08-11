"""Tests del parser SGF y de la generación de muestras de entrenamiento."""

import numpy as np

from motor import NEGRO, BLANCO
from entrenamiento.dataset import (
    cargar_directorio,
    construir_muestras,
    coord_a_fila_col,
    parsear_sgf,
)

SGF_BASICO = """(;GM[1]FF[4]SZ[9]KM[7.5]PB[robot]PW[robot]RE[B+12.5]
;B[dd];W[cc];B[dc])"""

SGF_CON_PASES = """(;GM[1]FF[4]SZ[9]RE[B+R];B[ee]W[];B[];W[ff])"""

SGF_CON_COMENTARIO = """(;GM[1]FF[4]SZ[9]RE[W+3.5]
;C[comentario con B[aa] que no es jugada]
;B[gg];W[hh])"""


def test_parsear_sgf_basico():
    datos = parsear_sgf(SGF_BASICO)
    assert datos["tamano"] == 9
    assert datos["resultado"] == "B+12.5"
    assert len(datos["movimientos"]) == 3
    assert datos["movimientos"][0] == (NEGRO, 3, 3)
    assert datos["movimientos"][1] == (BLANCO, 2, 2)
    assert datos["movimientos"][2] == (NEGRO, 3, 2)


def test_coord_sgf_omite_letra_i():
    assert coord_a_fila_col("aa", 9) == (0, 0)
    assert coord_a_fila_col("dd", 9) == (3, 3)
    # 'i' no existe en SGF
    assert coord_a_fila_col("ia", 9) is None
    # fuera del tablero 9x9 (k es la letra 10ª, índice 9)
    assert coord_a_fila_col("kk", 9) is None


def test_parsear_pases():
    datos = parsear_sgf(SGF_CON_PASES)
    assert datos["movimientos"][0] == (NEGRO, 4, 4)
    assert datos["movimientos"][1] == (BLANCO, None, None)
    assert datos["movimientos"][2] == (NEGRO, None, None)
    assert datos["movimientos"][3] == (BLANCO, 5, 5)


def test_comentario_no_genera_falsas_jugadas():
    datos = parsear_sgf(SGF_CON_COMENTARIO)
    assert len(datos["movimientos"]) == 2
    assert datos["movimientos"][0] == (NEGRO, 6, 6)


def test_construir_muestras_politica_y_valor():
    muestras = construir_muestras(parsear_sgf(SGF_BASICO))
    assert len(muestras) == 3
    # B juega dd en la posición vacía
    assert muestras[0]["color"] == NEGRO
    assert muestras[0]["etiqueta_politica"] == 3 * 9 + 3
    assert muestras[0]["etiqueta_valor"] == 1.0
    assert muestras[0]["canal"].shape == (5, 9, 9)
    # W juega cc (-1 pra a value 0)
    assert muestras[1]["color"] == BLANCO
    assert muestras[1]["etiqueta_politica"] == 2 * 9 + 2
    assert muestras[1]["etiqueta_valor"] == 0.0
    # B de nuevo
    assert muestras[2]["color"] == NEGRO
    assert muestras[2]["etiqueta_valor"] == 1.0


def test_construir_muestras_con_pases():
    muestras = construir_muestras(parsear_sgf(SGF_CON_PASES))
    # pases etiquetados con índice tamano² (82 para 9x9)
    assert any(m["es_pase"] for m in muestras)
    pase = next(m for m in muestras if m["es_pase"])
    assert pase["etiqueta_politica"] == 81


def test_movimiento_ilegal_se_omite():
    sgf = "(;SZ[9]RE[B+3.5];B[dd];B[dd];W[cc])"
    muestras = construir_muestras(parsear_sgf(sgf))
    # B[dd]; B[dd] ilegal (se omite sin avanzar); W[cc] válida → 2 muestras
    assert len(muestras) == 2
    assert muestras[0]["etiqueta_politica"] == 3 * 9 + 3
    assert muestras[1]["color"] == BLANCO


def test_cargar_directorio_filtra_no_nueve(tmp_path):
    (tmp_path / "buena.sgf").write_text(SGF_BASICO, encoding="utf-8")
    (tmp_path / "malota.sgf").write_text("(;SZ[19])", encoding="utf-8")
    datos = cargar_directorio(tmp_path)
    assert datos["partidas"] == 1
    assert len(datos["muestras"]) == 3
    assert datos["descartadas"] == 1


def test_cargar_directorio_vacio(tmp_path):
    datos = cargar_directorio(tmp_path)
    assert datos["partidas"] == 0
    assert datos["muestras"] == []