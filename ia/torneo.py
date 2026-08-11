"""Torneo round-robin entre configuraciones de IA.

Corre en paralelo muchas partidas rápidas (tablero pequeño, tiempo límite
corto) para comparar cada configuración contra las demás y agregar métricas por
configuración: victorias, derrotas, margen promedio, tiempo por jugada y
sims por segundo.

Uso típico:

    >>> resultado = torneo(["mcts-250", "mcts-l-250"], partidas=6)
    >>> resultado["resumen"]  # tabla agregada por configuración
"""

import itertools
from concurrent.futures import ProcessPoolExecutor

from motor import BLANCO, NEGRO
from .experimento import LIMITE_MOVIMIENTOS_POR_DEFECTO, construir_ia, jugar_partida

CONFIGS_POR_DEFECTO = ["aleatorio", "mcts-250", "mcts-800", "mcts-2000", "mcts-l-250", "mcts-l-800"]


def _crear_pool(procesos):
    """ProcessPoolExecutor con contexto fork (Linux): evita re-importar __main__."""
    import multiprocessing as mp
    return ProcessPoolExecutor(max_workers=procesos, mp_context=mp.get_context("fork"))


def _sims_de(config: str) -> int:
    """Simulaciones base declaradas por la config (sin aplicar handicaps)."""
    if config.startswith("mcts-l-"):
        return int(config.split("-")[2])
    if config.startswith("mcts-"):
        return int(config.split("-")[1])
    return 0


def _jugar_una(config_negro: str, config_blanco: str, semilla: int,
               tamano: int, komi: float, tiempo_limite_ms: int | None,
               limite_movimientos: int, persistir: bool) -> dict:
    """Una partida (worker de procesos): construye las IA y la juega."""
    negro = construir_ia(config_negro, tiempo_limite_ms)
    blanco = construir_ia(config_blanco, tiempo_limite_ms)
    if not persistir:
        return jugar_partida(negro, blanco, komi=komi, semilla=semilla,
                             tamano=tamano, limite_movimientos=limite_movimientos)

    def guardar(partida):
        from almacenamiento import store
        store.guardar_partida(
            partida,
            {NEGRO: config_negro, BLANCO: config_blanco},
            {"modo": "torneo", "tamano": tamano, "komi": komi,
             "simulaciones": max(_sims_de(config_negro), _sims_de(config_blanco)),
             "tiempo_limite_ms": tiempo_limite_ms})

    return jugar_partida(negro, blanco, komi=komi, semilla=semilla,
                         tamano=tamano, limite_movimientos=limite_movimientos,
                         al_final=guardar)


def _pares_round_robin(configs: list[str], partidas: int, semilla: int | None):
    """Genera enfrentamientos (negro, blanco, semilla) equilibrando colores.

    Cada pareja se juega ``partidas`` veces; la mitad con A como negro y la
    otra mitad con A como blanco, alternando por índice para evitar sesgo.
    """
    enfrentamientos = []
    indice = 0
    base = semilla if semilla is not None else 0
    for a, b in itertools.combinations(configs, 2):
        for i in range(partidas):
            sem = base + indice
            if i % 2 == 0:
                enfrentamientos.append((a, b, sem))
            else:
                enfrentamientos.append((b, a, sem))
            indice += 1
    return enfrentamientos


def torneo(configs: list[str] | None = None,
           partidas: int = 6,
           tamano: int = 7,
           komi: float = 7.5,
           tiempo_limite_ms: int | None = 700,
           semilla: int | None = None,
           limite_movimientos: int | None = None,
           procesos: int | None = None,
           persistir: bool = True) -> dict:
    """Torneo round-robin entre ``configs`` jugado con procesos en paralelo.

    ``persistir=True`` guarda cada partida en ``data/games`` (aparecen en el
    historial de la UI). Devuelve un dict con los enfrentamientos por pareja y
    un resumen con métricas agregadas por configuración.
    """
    configs = list(configs or CONFIGS_POR_DEFECTO)
    if len(configs) < 2:
        raise ValueError("se necesitan al menos dos configuraciones")

    if limite_movimientos is None:
        limite_movimientos = min(LIMITE_MOVIMIENTOS_POR_DEFECTO,
                                 max(30, tamano * tamano * 2))

    enfrentamientos = _pares_round_robin(configs, partidas, semilla)
    tareas = [
        (negro, blanco, sem, tamano, komi, tiempo_limite_ms,
         limite_movimientos, persistir)
        for negro, blanco, sem in enfrentamientos
    ]

    with _crear_pool(procesos) as pool:
        resultados = list(pool.map(_ejecutar_tarea, tareas))

    agregados = {c: _nuevo_acumulador(c) for c in configs}
    por_pareja = {}

    for (negro, blanco, sem), resultado in zip(enfrentamientos, resultados):
        clave = tuple(sorted((negro, blanco)))
        if clave not in por_pareja:
            por_pareja[clave] = {"negro": clave[0], "blanco": clave[1],
                                 "victorias": {clave[0]: 0, clave[1]: 0},
                                 "empates": 0, "partidas": 0}
        obs = por_pareja[clave]
        obs["partidas"] += 1
        _acumular(resultado, agregados, negro, blanco)
        ganador = resultado["ganador"]
        if ganador is None:
            obs["empates"] += 1
        elif ganador == NEGRO:
            obs["victorias"][negro] += 1  # negro real (config_negro)
        else:
            obs["victorias"][blanco] += 1

    resumen = [_resumen_config(c, d) for c, d in agregados.items()]
    resumen.sort(key=lambda r: -r["win_rate"])
    return {
        "configs": configs,
        "partidas_por_pareja": partidas,
        "tamano": tamano,
        "enfrentamientos": [f"{n} vs {b}: {v['victorias'][v['negro']]}-{v['victorias'][v['blanco']]}"
                            for n, b, _ in enfrentamientos
                            for v in [por_pareja[tuple(sorted((n, b)))]]],
        "resumen": resumen,
        "matriz": {f"{a} vs {b}": por_pareja.get(tuple(sorted((a, b)))) 
                   for a, b in itertools.combinations(configs, 2)},
    }


def _ejecutar_tarea(tarea):
    return _jugar_una(*tarea)


def _nuevo_acumulador(config: str) -> dict:
    return {
        "config": config,
        "victorias": 0,
        "derrotas": 0,
        "empates": 0,
        "tiempo_ms": 0.0,
        "movimientos": 0,
        "margenes": [],
        "sims": _sims_de(config),
        "jugadas_ia": 0,
    }


def _acumular(resultado: dict, agregados: dict, config_negro: str, config_blanco: str) -> None:
    """Suma el resultado de una partida a los acumuladores por configuración."""
    ganador = resultado["ganador"]
    tiempos = resultado["tiempos_ms"]
    for config, simbolo in ((config_negro, "B"), (config_blanco, "W")):
        a = agregados[config]
        lista = tiempos.get(simbolo, [])
        a["jugadas_ia"] += len(lista)
        a["tiempo_ms"] += sum(lista)
        a["movimientos"] += len(lista)

    if ganador is None:
        agregados[config_negro]["empates"] += 1
        agregados[config_blanco]["empates"] += 1
        return

    resultado_det = resultado.get("resultado") or {}
    totales = resultado_det.get("totales") or {}
    for config, color, etiqueta in (
            (config_negro, NEGRO, "negro"), (config_blanco, BLANCO, "blanco")):
        if ganador == color:
            agregados[config]["victorias"] += 1
        else:
            agregados[config]["derrotas"] += 1
        if "negro" in totales and totales["negro"] is not None:
            dif = totales[etiqueta] - totales["blanco" if etiqueta == "negro" else "negro"]
            agregados[config]["margenes"].append(round(dif, 1))


def _resumen_config(config: str, a: dict) -> dict:
    total = a["victorias"] + a["derrotas"] + a["empates"]
    tiempo_prom = round(a["tiempo_ms"] / a["jugadas_ia"], 2) if a["jugadas_ia"] else 0.0
    sims_por_segundo = round(a["sims"] / (tiempo_prom / 1000.0), 1) if tiempo_prom > 0 else 0.0
    margen_prom = round(sum(a["margenes"]) / len(a["margenes"]), 2) if a["margenes"] else None
    return {
        "config": config,
        "partidas": total,
        "victorias": a["victorias"],
        "derrotas": a["derrotas"],
        "empates": a["empates"],
        "win_rate": round(a["victorias"] / total, 3) if total else 0.0,
        "margen_promedio": margen_prom,
        "tiempo_promedio_ms": tiempo_prom,
        "sims": a["sims"],
        "sims_por_segundo": sims_por_segundo,
    }