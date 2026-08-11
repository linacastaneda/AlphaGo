# PLAN — Aplicación web de Go inspirada en AlphaGo (simplificado)

> **Stack:** Python + Flask | **Tablero:** 9×9 (komi 7.5, conteo por área, ko simple, superko opcional) | **Persistencia:** JSON con coordenadas + métricas | **Suite de tests:** `pytest`.

## Pipeline general del proyecto

```text
PARTIDAS HISTÓRICAS SGF (data/historical/)
        ↓
MCTS + UCT (heurístico) con playouts
        ↓
APLICACIÓN WEB (Flask)
        ↓
SELF-PLAY (IA vs IA, data/games/)
        ↓
ANÁLISIS Y COMPARACIÓN ENTRE CONFIGURACIONES DE IA
```

## Honestidad técnica

Es una arquitectura **simplificada inspirada en AlphaGo** (MCTS + UCT). No incluye redes neuronales, TPU ni el pipeline RL distribuido del original.

## Estructura del proyecto

```text
AlphaGo/
├── app.py                        # Flask: rutas + middleware de instrumentación (latencia, memoria)
├── requirements.txt              # flask + pytest
├── PLAN.md
├── README.md
├── motor/
│   ├── board.py                  # Estado del tablero, grupos, libertades, capturas, ko
│   └── scoring.py                # Fin de partida (doble pase) y conteo por área, komi 7.5
├── ia/
│   ├── mcts.py                   # MCTS + UCT (baseline heurístico con playouts)
│   ├── mcts_lina.py              # MCTS estilo académico (rollout aleatorio puro)
│   ├── rival_lina.py             # Adaptador MCTS L (handicap de simulaciones)
│   ├── experimento.py            # Comparativas entre configuraciones de IA
│   ├── torneo.py                 # Torneo round-robin paralelo entre configuraciones
│   └── rollout.py                # Simulación aleatoria/heurística de final de partida
├── almacenamiento/
│   ├── store.py                  # Persistencia JSON de partidas + historial + rankings
│   └── perf.py                   # Métricas de rendimiento de la propia app (log rodante)
├── static/
│   ├── index.html                # Tablero SVG, controles, replay, dashboard
│   ├── css/style.css
│   └── js/
│       ├── tablero.js            # Render SVG + interacción clic
│       ├── juego.js              # Llamadas API, estado de la partida
│       ├── interfaz.js           # Navegación entre pestañas
│       ├── repeticion.js         # Reproducción frame a frame (velocidad, saltos)
│       └── metricas.js           # Gráficas con Chart.js (CDN) + torneo
├── data/
│   ├── games/                    # Partidas JSON generadas por la aplicación
│   ├── historical/               # SGF de partidas (históricas o de self-play)
│   └── historial.json            # Historial agregado + rankings
└── pruebas/
    ├── test_engine.py            # Capturas, suicidio, ko, puntuación
    ├── test_mcts.py              # Selección, expansión, retropropagación
    ├── test_rival_lina.py        # MCTS L (port de Lina) y su adaptador
    ├── test_experimento.py       # Comparativas de configuraciones
    ├── test_api.py               # Endpoints principales
    └── test_storage.py           # Persistencia y rankings
```

---

## Formato de guardado de partida (JSON)

```json
{
  "id": "...",
  "board_size": 9,
  "komi": 7.5,
  "players": { "B": "human", "W": "mcts-800" },
  "moves": [
    {
      "player": "B",
      "coord": [3, 4],
      "captures": 1,
      "move_ms": 120,
      "ai": {
        "sims": 800,
        "time_ms": 115,
        "win_rate": 0.52,
        "nodes": 213
      },
      "perf": { "api_ms": 4 }
    }
  ],
  "result": {
    "winner": "B",
    "score": 12.5,
    "captures": { "B": 3, "W": 1 },
    "duration_s": 245
  }
}
```

Esto habilita: **replay, historial, rankings, análisis posterior y comparación entre configuraciones de IA**.

---

## API REST

```text
POST /api/game/new
POST /api/game/<id>/move
POST /api/game/<id>/pass
POST /api/game/<id>/resign
POST /api/game/<id>/ai-move
POST /api/ai/experiment        # Duelo entre configuraciones (p. ej. mcts-250 vs mcts-l-250)
POST /api/ai/torneo            # Torneo round-robin paralelo entre configuraciones
POST /api/game/<id>/analysis   # Análisis de posición: top jugadas con win-rate

GET  /api/game/<id>
GET  /api/games                # historial + rankings
GET  /api/metrics              # métricas de partida y de IA
GET  /api/perf                 # latencias, memoria, tiempos de IA
```

El motor valida todas las jugadas; la IA devuelve sus métricas junto al movimiento.

---

## Fases y TODOs

### Fase A — Jugar temprano (motor + infraestructura)

- [x] **A1. Motor del juego** `motor/board.py` + `motor/scoring.py`
  - [x] Tablero 9×9, grupos/conectividad, libertades
  - [x] Capturas, regla de suicidio
  - [x] Ko simple (superko opcional)
  - [x] Fin por doble pase
  - [x] Conteo por área, komi 7.5
  - [x] Tests unitarios en `pruebas/test_engine.py`
- [x] **A2. Persistencia JSON** `almacenamiento/store.py` + `almacenamiento/perf.py`
  - [x] Guardar/leer partidas en `data/games/<id>.json`
  - [x] `data/historial.json` para historial y rankings
  - [x] Log rodante de métricas de rendimiento de la app (`perf.py`)
- [x] **A3. MCTS baseline** `ia/mcts.py`
  - [x] Selección, expansión, simulación, retropropagación, UCT
  - [x] Playouts aleatorios + heurísticas ligeras (capturas, libertades, filtro de movimientos inútiles)
  - [x] Parámetros configurables: 250 / 800 / 2000 simulaciones
  - [x] KPIs: time_ms, sims, nodes, win_rate
  - [x] Tests en `pruebas/test_mcts.py`
- [x] **A4. API REST Flask** `app.py`
  - [x] Endpoints de la sección API
  - [x] Middleware de instrumentación (latencia por endpoint, memoria)
  - [x] `pruebas/test_api.py`
- [x] **A5. Frontend visual** `static/`
  - [x] Tablero SVG interactivo (clic para colocar)
  - [x] Modos: PvP, humano vs IA, IA vs IA, duelo MCTS vs MCTS L
  - [x] Controles: colocar, pasar, rendirse, nueva partida, selector de simulaciones, selector de IA
  - [x] Panel en vivo: turno, capturas, puntuación, sims, nodos, tiempo de decisión, win-rate estimado
- [x] **A6. Replay** `static/js/repeticion.js`
  - [x] Velocidad ajustable, anterior/siguiente, saltar al movimiento N
  - [x] Mostrar coordenadas y métricas por movimiento
  - [x] Reconstrucción re-aplicando coordenadas del JSON
- [x] **A7. Métricas de app + dashboard** `static/js/metricas.js`
  - [x] `GET /api/perf` con latencias, memoria, tiempos de IA
  - [x] Dashboard con Chart.js: rankings, win-rates

### Fase B — IA y comparativas

- [x] **B8. MCTS L (port de Lina)** `ia/mcts_lina.py` + `ia/rival_lina.py`
  - [x] MCTS estilo académico (UCT clásico + rollout aleatorio puro) sobre nuestro motor
  - [x] Handicap de simulaciones aplicado en el adaptador (config `mcts-l-<sims>`)
  - [x] Modo duelo MCTS vs MCTS L en la app
  - [x] Tests en `pruebas/test_rival_lina.py`
- [x] **B9. Experimento** endpoint `/api/ai/experiment` + `ia/experimento.py`
  - [x] Harness: configs `aleatorio`, `mcts-<sims>`, `mcts-l-<sims>`; partidas con semilla
  - [x] Agrega victorias, empates, movimientos y tiempos promedio por jugador
  - [x] Tests en `pruebas/test_experimento.py`
- [x] **B10. Torneo round-robin** `ia/torneo.py`
  - [x] Partidas paralelas (ProcessPool) entre configuraciones
  - [x] Resumen por configuración: victorias, derrotas, margen, tiempo por jugada, sims/s
  - [x] Persistencia de partidas en `data/games/`

---

## Configuración experimental

- **Experimento 1 — MCTS baseline:** 250 vs 800 vs 2000 simulaciones (medir tiempo, nodos, win-rate).
- **Experimento 2 — Baseline vs MCTS L:** `mcts-<sims>` vs `mcts-l-<sims>` con el handicap del adaptador.
- **Torneo:** round-robin entre `aleatorio`, `mcts-*` y `mcts-l-*`.

## Convención de código

**Todo el código en español**: nombres de funciones, variables, clases, comentarios, mensajes de error y de UI. Ejemplos: `colocar_piedra()`, `calcular_libertades`, `jugar_movimiento()`, `Tablero`, `partida`, `turno`, `capturas`, `puntaje`. Los identificadores técnicos (JSON, API, MCTS, SGF) se conservan en inglés por ser nombres propios de librerías/protocolos.

## Restricciones ambientales / cómo ejecutar

- Backend: `pip install -r requirements.txt` (`flask` + `pytest`).
- Módulo de python para rutas: usar rutas absolutas/relativas al repo base (todas las operaciones de archivo relativas al workspace).
- Cheats: `pytest pruebas/` desde la raíz del proyecto.
- App: `python app.py` (Flask en `127.0.0.1:5000`).

## Notas de diseño (pendientes durante implementación)

- Superko: v1 ko simple; opcional.
- Handicap MCTS L: `HANDICAP_LINA = 3` multiplica las simulaciones efectivas (su rollout aleatorio puro es más débil que el heurístico a igualdad de simulaciones).
