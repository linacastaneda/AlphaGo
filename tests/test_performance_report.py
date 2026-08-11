"""Tests del generador de informe de desempeño (D17)."""

from analysis.performance_report import generar_markdown, md_a_html


def _datos_minimos() -> dict:
    return {
        "fecha": "2026-01-01 10:00",
        "fuente": "disco",
        "perf": {
            "endpoints": {"GET /": {"count": 2, "promedio_ms": 1.0, "p95_ms": 1.5}},
            "total_mediciones": 2,
            "memoria_promedio_kb": 2048,
            "max_memoria_kb": 4096,
        },
        "rankings": {"rankings": [{"jugador": "humano", "victorias": 1,
                                    "derrotas": 0, "win_rate": 1.0}]},
        "estadisticas_ia": {"estadisticas_ia": []},
        "partidas": [],
        "_total_partidas": 0,
        "experimentos": [],
        "versiones_modelo": [],
        "models_meta": {"versiones": []},
    }


def test_markdown_tiene_secciones_clave():
    md = generar_markdown(_datos_minimos())
    for encabezado in ["## 1. Arquitectura", "## 4. Latencia de la aplicación",
                       "## 8. Estado de las redes", "## 13. Conclusiones"]:
        assert encabezado in md
    assert "renderizados pendientes" in md
    assert "servidor" in md or "disco" in md


def test_markdown_con_ranking_y_benchmark():
    datos = _datos_minimos()
    datos["benchmark"] = [{"sims": 50, "tiempo_ms": 100.0, "nodos": 80,
                           "sims_por_segundo": 500.0}]
    datos["experimentos"] = [{"negro": "aleatorio", "blanco": "mcts-150",
                              "partidas": 2, "win_rate_negro": 0.5}]
    md = generar_markdown(datos)
    assert "| Jugador | V | D | Win-rate % |" in md
    assert "mcts-150" in md
    assert "×" in md or "escala" in md


def test_html_convierte_tablas():
    md = ("# Título\n\n| A | B |\n| --- | --- |\n| 1 | 2 |\n\n## Sección\n")
    html = md_a_html(md)
    assert "<h1>Título</h1>" in html
    assert html.count("<table>") == 1
    assert "<th>A</th>" in html
    assert "<td>1</td>" in html
    assert "<h2>Sección</h2>" in html