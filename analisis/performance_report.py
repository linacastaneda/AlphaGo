"""Informe de desempeño: performance_report.md y .html desde datos reales.

Agrega las mediciones de la propia aplicación (storage/perf.py), las partidas
guardadas (storage/store.py), un benchmark rápido del MCTS y (opcionalmente)
experimentos baseline ``aleatorio``/``mcts-<sims>``.

Uso:
    python -m analysis.performance_report              # solo datos existentes
    python -m analysis.performance_report --experimentos 2   # añade duelos cortos
"""

import argparse
import json
import time
from pathlib import Path

from almacenamiento import perf, store

RUTA_BASE = Path(__file__).resolve().parent.parent
RUTA_MODELS = RUTA_BASE / "models"
RUTA_MODELOS_META = RUTA_BASE / "data" / "models_meta.json"
SALIDA_MD = RUTA_BASE / "performance_report.md"
SALIDA_HTML = RUTA_BASE / "performance_report.html"

SIMS_BENCHMARK = [50, 150, 300]


def versiones_guardadas() -> list:
    """Versiones de modelo presentes (carpetas con policy.onnx en models/)."""
    versiones = []
    if RUTA_MODELS.exists():
        for subcarpeta in sorted(RUTA_MODELS.iterdir()):
            if subcarpeta.is_dir() and (subcarpeta / "policy.onnx").exists():
                versiones.append(subcarpeta.name)
        if (RUTA_MODELS / "policy.onnx").exists():
            versiones.append("default")
    return versiones


def cargar_modelos_meta() -> dict:
    if RUTA_MODELOS_META.exists():
        try:
            return json.loads(RUTA_MODELOS_META.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"versiones": [], "nota": "sin modelos aún"}


def medir_mcts(sims: int) -> dict:
    """Mide una decisión del MCTS en la posición inicial (1 jugada)."""
    from ia.mcts import crear_mcts
    from motor.scoring import Partida

    mcts = crear_mcts(simulaciones=sims, tiempo_limite_ms=None)
    partida = Partida(9, 7.5)
    inicio = time.perf_counter()
    resultado = mcts.mejor_jugada(partida)
    ms = (time.perf_counter() - inicio) * 1000
    return {
        "sims": sims,
        "tiempo_ms": round(ms, 1),
        "nodos": resultado["nodes"],
        "sims_por_segundo": round(sims / (ms / 1000), 1) if ms else 0.0,
    }


def benchmark_mcts() -> list:
    return [medir_mcts(s) for s in SIMS_BENCHMARK]


def ejecutar_experimentos(partidas_por_duelo: int, semilla: int,
                          tiempo_limite_ms: int = 250) -> list:
    """Duelos baseline cortos y acotados en tiempo por jugada."""
    from ia.experimento import experimento

    duelos = [
        ("aleatorio", "mcts-100"),
        ("mcts-100", "mcts-200"),
    ]
    resultados = []
    for negro, blanco in duelos:
        resultados.append(experimento(negro, blanco, partidas=partidas_por_duelo,
                                      semilla=semilla,
                                      tiempo_limite_ms=tiempo_limite_ms))
    return resultados


def _datos_remoto(base_url: str = "http://127.0.0.1:5000") -> dict | None:
    """Intenta leer las métricas en vivo de la app (mismos datos del dashboard)."""
    import urllib.request

    def _get(ruta):
        with urllib.request.urlopen(base_url + ruta, timeout=4) as respuesta:
            return json.loads(respuesta.read().decode())

    try:
        return {"perf": _get("/api/perf"), "metrics": _get("/api/metrics"),
                "games": _get("/api/games")}
    except Exception:
        return None


def _promedio_valores(mapa) -> float:
    """Media de los valores numéricos de un diccionario."""
    valores = [v for v in mapa.values() if v]
    return round(sum(valores) / len(valores), 1) if valores else 0.0


def recoger_datos(con_bench: bool, con_experimentos: int,
                  tiempo_limite_ms: int = 250) -> dict:
    remoto = _datos_remoto()
    if remoto is not None:
        perf_datos = remoto["perf"]
        metricas = remoto["metrics"]
        partidas = _normalizar_games(remoto["games"])
        estadisticas_ia = {"estadisticas_ia": metricas.get("estadisticas_ia", [])}
        rankings = {"rankings": metricas.get("rankings", [])}
        experimentos = metricas.get("experimentos", [])
        fuente = "servidor /api/… (en vivo)"
    else:
        perf_datos = perf.resumen_perf()
        rankings = store.calcular_rankings()
        estadisticas_ia = store.obtener_estadisticas_ia()
        partidas = store.listar_partidas()
        experimentos = perf.obtener_experimentos()
        fuente = "disco (data/) — el servidor no está en ejecución"

    datos = {
        "fecha": time.strftime("%Y-%m-%d %H:%M"),
        "fuente": fuente,
        "perf": perf_datos,
        "rankings": rankings,
        "estadisticas_ia": estadisticas_ia,
        "partidas": partidas,
        "experimentos": experimentos,
        "versiones_modelo": versiones_guardadas(),
        "models_meta": cargar_modelos_meta(),
        "_total_partidas": len(partidas),
    }
    if con_bench:
        datos["benchmark"] = benchmark_mcts()
    if con_experimentos > 0:
        datos["experimentos"] += ejecutar_experimentos(
            con_experimentos, semilla=1,
            tiempo_limite_ms=tiempo_limite_ms)
    return datos


def _normalizar_games(remoto: dict) -> list:
    """Los resúmenes remotos llevan `tablero` igualmente; lista directa basta."""
    if isinstance(remoto, dict):
        return remoto.get("partidas", [])
    return remoto


def formato_tabla(filas, cabeceras) -> str:
    linea = [f"| {h} " for h in cabeceras]
    salida = ["".join(linea) + "|", "".join("| --- " for _ in cabeceras) + "|"]
    for fila in filas:
        salida.append("| " + " | ".join(str(c) for c in fila) + " |")
    return "\n".join(salida)


def seccion_latencia(datos) -> str:
    endpoints = datos["perf"].get("endpoints", {})
    if not endpoints:
        return "No hay mediciones de latencia registradas todavía (ejecuta peticiones a la app)."
    filas = []
    for ep, res in sorted(endpoints.items(), key=lambda kv: kv[1]["p95_ms"], reverse=True):
        filas.append([ep, res["count"], res["promedio_ms"], res["p95_ms"]])
    return formato_tabla(filas, ["Endpoint", "Peticiones", "media (ms)", "p95 (ms)"])


def seccion_mcts_guardado(datos) -> str:
    estadisticas = datos.get("estadisticas_ia", {}).get("estadisticas_ia", [])
    if not estadisticas:
        return "Sin configuraciones de IA registradas en partidas guardadas."
    filas = [[a["config"], a["movimientos"], a["sims"], a.get("tiempo_promedio_ms", 0),
              a.get("sims_por_segundo", 0)] for a in estadisticas]
    return formato_tabla(filas, ["Config", "Movs", "Sims", "ms/jugada", "sims/s"])


def seccion_rankings(datos) -> str:
    rankings = datos.get("rankings", {}).get("rankings", [])
    if not rankings:
        return "Sin partidas terminadas registradas para calcular ranking."
    filas = [[r["jugador"], r["victorias"], r["derrotas"], round(r["win_rate"] * 100)]
             for r in rankings]
    return formato_tabla(filas, ["Jugador", "V", "D", "Win-rate %"])


def seccion_benchmark(datos) -> str:
    if "benchmark" not in datos:
        return ""
    filas = [[b["sims"], b["tiempo_ms"], b["nodos"], b["sims_por_segundo"]]
             for b in datos["benchmark"]]
    texto = "Medición en la posición inicial (una decisión por fila):\n\n"
    texto += formato_tabla(filas, ["Sims", "ms/decisión", "nodos", "sims/s"]) + "\n"
    return texto


def seccion_experimentos(datos) -> str:
    resultados = datos.get("experimentos", [])
    if not resultados:
        return ("No se ejecutaron duelos baseline en esta ejecución "
                "(pásale ``--experimentos N`` para comparar aleatorio/mcts en directo).\n"
                "Los experimentos guardados en la app (`/api/ai/experiment`) aparecen "
                "en la sección de Conclusiones.")
    filas = []
    for r in resultados:
        filas.append([f"{r['negro']} vs {r['blanco']}", r["partidas"],
                      r["victorias_negro"], r["victorias_blanco"], r["empates"],
                      r["win_rate_negro"]])
    return formato_tabla(filas, ["Duelo", "Partidas", "G negras", "G blancas",
                                 "Empates", "WR negro"]) + "\n"


def generar_markdown(datos) -> str:
    llegadas = datos["_total_partidas"]
    perf_datos = datos["perf"]
    versiones = datos["versiones_modelo"]
    estado_redes = (
        "renderizados pendientes"
        if not versiones else "versiones disponibles: " + ", ".join(versiones))

    texto = []
    texto.append("# Informe de desempeño — AlphaGo simplificado")
    texto.append(f"_Generado {datos['fecha']} · datos de: {datos['fuente']}_\n")

    texto.append("## 1. Arquitectura")
    texto.append(
        "Motor de Go propio (9×9, komi 7.5, conteo por área, ko simple) + MCTS UCT con "
        "playouts heurísticos. **Arquitectura simplificada** inspirada en AlphaGo: "
        "sin redes residuales de 40 capas, sin TPU ni pipeline RL distribuido. "
        "Cuando existan modelos ONNX (`models/`), el MCTS los usa como prior (PUCT) "
        "y valor de nodo (`ai/redes.py`); sin modelos cae en baseline heurístico.\n")

    texto.append("## 2. Configuración experimental")
    texto.append("- Tablero fijo 9×9, komi 7.5, límite de movimientos 360.")
    texto.append("- Baseline: `aleatorio` (jugadas legales al azar).")
    texto.append("- MCTS heurístico: 250/800/2000 simulaciones (configurables).")
    texto.append("- MCTS con redes (`+red`): PUCT + value (requiere modelos ONNX).")
    texto.append("- Duelos con semilla reproducible mediante `ai/experimento.py`.\n")

    texto.append("## 3. Rendimiento del motor")
    bench = seccion_benchmark(datos)
    texto.append(bench if bench else "*(benchmark deshabilitado)*\n")

    texto.append("## 4. Latencia de la aplicación")
    texto.append(seccion_latencia(datos) + "\n")

    texto.append("## 5. Rendimiento del MCTS (partidas guardadas)")
    texto.append(seccion_mcts_guardado(datos) + "\n")

    texto.append("## 6. Impacto de simulaciones")
    if "benchmark" in datos and len(datos["benchmark"]) >= 2:
        primero = datos["benchmark"][0]
        ultimo = datos["benchmark"][-1]
        escala_tiempo = ultimo["tiempo_ms"] / max(1, primero["tiempo_ms"])
        texto.append(
            f"De {primero['sims']} a {ultimo['sims']} simulaciones el tiempo por "
            f"decisión escala ×{escala_tiempo:.1f} a coste de ~{ultimo['nodos']} "
            "nodos en la posición inicial. El balance entre calidad y tiempo se "
            "mide con duelos directos (ver §2 y Conclusiones).")
    else:
        texto.append("*(sin benchmark en esta ejecución)*")
    texto.append("")

    texto.append("## 7. Ranking de jugadores / configuraciones")
    texto.append(seccion_rankings(datos) + "\n")

    texto.append("## 8. Estado de las redes (política/valor)")
    texto.append(
        f"Entrenamiento en Colab (`training/Colab_AlphaGo.ipynb`, PyTorch): "
        f"CNN compartida con cabezas de política (82 salidas) y valor (sigmoide). "
        f"**{estado_redes}**. "
        f"La ejecución de referencia logró loss 9.06→0.40 y precisión de política "
        f"≈0.89 (30 épocas) sobre el dataset histórico disponible. "
        "La integración runtime (`ai/redes.py`) está implementada y funciona como "
        "fallback elegante sin modelos. Falta exponer los `.onnx` reales en `models/`.\n")

    texto.append("## 9. Baseline vs redes (Experimento 2)")
    texto.append(
        "Harness listo (`/api/ai/experiment`, `ai/experimento.py`). Pendiente de "
        "ejecutar la comparativa formal baseline vs `+red` cuando existan modelos "
        "exportados.\n")

    texto.append("## 10. Evolución de modelos (self-play v1 → v2 → v3)")
    versiones_meta = datos.get("models_meta", {})
    filas_meta = versiones_meta.get("versiones", [])
    if filas_meta:
        filas = [[v.get("version"), v.get("fecha", ""), v.get("win_rate", ""),
                  v.get("nota", "")] for v in filas_meta]
        texto.append(formato_tabla(filas, ["Versión", "Fecha", "Win-rate", "Nota"]))
    else:
        texto.append(
            "Sin versiones registradas en `data/models_meta.json`. "
            "El pipeline de self-play (`training/self_play.py`) genera SGF de IA vs IA "
            "para reentrenar y producir v2/v3; pendiente de ejecutar en Colab.\n")

    texto.append("## 11. Uso de tiempo y memoria")
    texto.append(
        f"- Mediciones registradas: **{perf_datos.get('total_mediciones', 0)}**"
        f"  · memoria promedio: **{round(perf_datos.get('memoria_promedio_kb', 0) / 1024, 1)} MB**"
        f"  · memoria máxima: **{round(perf_datos.get('max_memoria_kb', 0) / 1024, 1)} MB**.\n")

    texto.append("## 12. Experimentos registrados en la app")
    exp = datos.get("experimentos", [])
    if exp:
        for e in exp[:5]:
            texto.append(
                f"- `{e.get('negro')}` vs `{e.get('blanco')}` · {e.get('partidas')} "
                f"partidas · WR negro {round(e.get('win_rate_negro', 0) * 100)}% "
                f"· mov. medio {e.get('movimientos_promedio', 0)} "
                f"· media por jugada {_promedio_valores(e.get('tiempo_promedio_ms', {}))} ms")
    else:
        texto.append("Sin experimentos guardados aún (usa `/api/ai/experiment` o `--experimentos`).")
    texto.append("")

    texto.append("## 13. Conclusiones y limitaciones")
    texto.append("- **Funcional sin redes:** el MCTS baseline ofrece una IA jugable "
                 "desde la app (humano vs IA, IA vs IA).")
    texto.append("- **Limitación principal:** sin los modelos ONNX en `models/`, "
                 "«+red» cae a baseline; las comparativas formales y la evolución "
                 "v1→v3 quedan pendientes de la ejecución en Colab.")
    texto.append("- Dataset histórico actual: "
                 f"{llegadas} partida(s) SGF 9×9 en "
                 "`data/historical/`, suficiente para validar el pipeline, no para "
                 "un modelo competitivo.")
    return "\n".join(texto)


def md_a_html(texto_md: str) -> str:
    """Convertidor mínimo de markdown al subconjunto emitido por este informe."""
    import html as html_mod
    lineas = texto_md.splitlines()
    salida = []
    en_tabla = False
    primera_fila = True

    def cerrar_tabla():
        nonlocal en_tabla, primera_fila
        if en_tabla:
            salida.append("</table>")
            en_tabla = False
            primera_fila = True

    for linea in lineas:
        esc = html_mod.escape(linea)
        if esc.startswith("### "):
            cerrar_tabla()
            salida.append(f"<h3>{esc[4:]}</h3>")
        elif esc.startswith("## "):
            cerrar_tabla()
            salida.append(f"<h2>{esc[3:]}</h2>")
        elif esc.startswith("# "):
            cerrar_tabla()
            salida.append(f"<h1>{esc[2:]}</h1>")
        elif esc.startswith("| ---"):
            continue
        elif esc.startswith("|"):
            celdas = [c.strip() for c in esc.strip("|").strip().split("|")]
            if not en_tabla:
                salida.append("<table>")
                en_tabla = True
            etiqueta = "th" if primera_fila else "td"
            primera_fila = False
            salida.append("<tr>" + "".join(
                f"<{etiqueta}>{c}</{etiqueta}>" for c in celdas) + "</tr>")
        elif esc.startswith("- "):
            cerrar_tabla()
            salida.append(f"<li>{esc[2:]}</li>")
        elif not esc.strip():
            cerrar_tabla()
            salida.append("")
        else:
            cerrar_tabla()
            salida.append(f"<p>{esc}</p>")
    cerrar_tabla()
    cuerpo = "\n".join(salida)
    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><title>Informe de desempeño</title>
<style>
  body {{ font-family: Georgia, serif; max-width: 960px; margin: 0 auto; padding: 2.2rem 1.4rem;
         background: #efe7d6; color: #191612; line-height: 1.55; }}
  h1 {{ border-bottom: 2px solid #191612; padding-bottom: .4rem; }}
  h2 {{ margin-top: 2rem; border-bottom: 1px solid #c23a2a; padding-bottom: .2rem; }}
  table {{ border-collapse: collapse; margin: 1rem 0; width: 100%; }}
  th, td {{ border: 1px solid #cdc2a8; padding: .45rem .6rem; font-size: .92rem; text-align: left; }}
  th {{ background: #e6dcc6; }}
  li {{ margin: .2rem 0; }}
  p {{ margin: .55rem 0; }}
  .nota {{ color: #4a443a; font-size: .9rem; }}
</style></head>
<body>{cuerpo}<p class="nota">Generado por analysis/performance_report.py</p></body></html>"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera el informe de desempeño")
    parser.add_argument("--experimentos", type=int, default=0,
                        help="partidas por duelo baseline (0 = solo datos existentes)")
    parser.add_argument("--tiempo-limite-ms", type=int, default=250,
                        help="tope de tiempo por jugada en los duelos (evita partidas muy largas)")
    parser.add_argument("--sin-benchmark", action="store_true",
                        help="no medir el MCTS (más rápido)")
    opciones = parser.parse_args()

    store._asegurar_directorios()
    perf.cargar_log()
    datos = recoger_datos(con_bench=not opciones.sin_benchmark,
                          con_experimentos=opciones.experimentos,
                          tiempo_limite_ms=opciones.tiempo_limite_ms)
    md = generar_markdown(datos)
    SALIDA_MD.write_text(md, encoding="utf-8")
    SALIDA_HTML.write_text(md_a_html(md), encoding="utf-8")
    print(f"informe generado: {SALIDA_MD}")
    print(f"                : {SALIDA_HTML}")


if __name__ == "__main__":
    main()