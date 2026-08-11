# PLAN — Aplicación web de Go inspirada en AlphaGo (simplificado)

> **Stack:** Python + Flask | **Tablero:** 9×9 (komi 7.5, conteo por área, ko simple, superko opcional) | **Inferencia:** ONNX Runtime local | **Entrenamiento:** Google Colab (`.ipynb`) | **Persistencia:** JSON con coordenadas + métricas | **Suite de tests:** `pytest`.

## Pipeline general del proyecto

```text
PARTIDAS HISTÓRICAS SGF
        ↓
ENTRENAMIENTO EN COLAB (policy + value + export ONNX)
        ↓
POLICY.ONNX + VALUE.ONNX
        ↓
MCTS + Policy + Value
        ↓
APLICACIÓN WEB
        ↓
SELF-PLAY (IA vs IA)
        ↓
NUEVAS VERSIONES DEL MODELO (v1 → v2 → v3)
        ↓
ANÁLISIS DE DESEMPEÑO (performance_report.md / .html)
```

## Honestidad técnica

Es una arquitectura **simplificada inspirada en AlphaGo** (MCTS + Policy + Value + self-play). No incluye las redes residuales de ~40 capas, TPU, ni el pipeline RL distribuido del original. El informe de desempeño debe decirlo explícitamente.

## Estructura del proyecto

```text
AlphaGo/
├── app.py                        # Flask, rutas + middleware de instrumentación (latencia, tracemalloc)
├── requirements.txt              # flask + onnxruntime (inferencia ligera)
├── PLAN.md
├── README.md
├── engine/
│   ├── board.py                  # Estado del tablero, grupos, libertades, capturas, ko
│   └── scoring.py                # Fin de partida (doble pase) y conteo por área, komi 7.5
├── ai/
│   ├── mcts.py                   # MCTS + UCT (baseline heurístico y guiado por redes)
│   ├── redes.py                  # Inferencia Policy/Value vía ONNX + codificación (fallback)
│   ├── experimento.py            # Comparativas de configs: baseline vs redes vs aleatorio
│   └── rollout.py                # Simulación aleatoria/heurística de final de partida
├── models/
│   └── (policy.onnx, value.onnx por versión, p. ej. v2/)
├── training/
│   ├── download_dataset.py       # Descarga SGF 9×9 públicos → data/historical/
│   ├── dataset.py                # Parser SGF → posiciones (canales) + etiquetas
│   ├── nets.py                   # CNN pequeña (policy + value) y export a ONNX
│   ├── self_play.py              # IA vs IA → data/training/
│   └── Colab_AlphaGo.ipynb       # Notebook completo (dataset → policy → value → onnx → self-play)
├── storage/
│   ├── store.py                  # Persistencia JSON de partidas + historial + rankings
│   └── perf.py                   # Métricas de rendimiento de la propia app (log rodante)
├── static/
│   ├── index.html                # Tablero SVG, controles, replay, dashboard
│   ├── css/style.css
│   └── js/
│       ├── board.js              # Render SVG + interacción clic
│       ├── game.js               # Llamadas API, estado de la partida
│       ├── replay.js             # Reproducción frame a frame (velocidad, saltos)
│       └── metrics.js            # Gráficas con Chart.js (CDN)
├── data/
│   ├── games/                    # Partidas JSON generadas por la aplicación
│   ├── historical/               # Dataset SGF de partidas históricas
│   ├── training/                 # Datos generados mediante self-play
│   └── models_meta.json          # Versiones de modelo y sus resultados
├── analysis/
│   └── performance_report.py     # Genera performance_report.md y performance_report.html
└── tests/
    ├── test_engine.py            # Capturas, suicidio, ko, puntuación
    ├── test_mcts.py              # Selección, expansión, retropropagación
    └── test_api.py               # Endpoints principales
```

---

## Formato de guardado de partida (JSON)

```json
{
  "id": "...",
  "board_size": 9,
  "komi": 7.5,
  "players": { "B": "human", "W": "alphago_simplified" },
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
        "nodes": 213,
        "policy_confidence": 0.41,
        "value_estimate": 0.58
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
POST /api/ai/experiment        # Experimento 2: baseline vs baseline+redes
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

- [ ] **A1. Motor del juego** `engine/board.py` + `engine/scoring.py`
  - [ ] Tablero 9×9, grupos/conectividad (union-find o BFS), libertades
  - [ ] Capturas, regla de suicidio
  - [ ] Ko simple v1 (superko opcional)
  - [ ] Fin por doble pase
  - [ ] Conteo por área, komi 7.5
  - [ ] Tests unitarios de casos clásicos (captura larga, ko, ojo falso, seki) en `tests/test_engine.py`
- [ ] **A2. Persistencia JSON** `storage/store.py` + `storage/perf.py`
  - [ ] Guardar/leer partidas en `data/games/<id>.json` (esquema de arriba)
  - [ ] `history.json` para historial y rankings
  - [ ] Log rodante de métricas de rendimiento de la app (`perf.py`)
- [ ] **A3. MCTS baseline** `ai/mcts.py`
  - [ ] Selección, expansión, simulación, retropropagación, UCT
  - [ ] Playouts aleatorios + heurísticas ligeras: priorizar capturas, evitar suicidio, valorar libertades, filtrar movimientos inútiles
  - [ ] Parámetros configurables: 250 / 800 / 2000 simulaciones
  - [ ] KPIs: time_ms, sims, nodes, sims/s, win_rate
  - [ ] Tests en `tests/test_mcts.py` (selección, expansión, retropropagación)
- [ ] **A4. API REST Flask** `app.py`
  - [ ] Endpoints de la sección API (new, move, pass, resign, ai-move, games, metrics, perf)
  - [ ] Middleware de instrumentación (latencia por endpoint, tracemalloc)
  - [ ] `tests/test_api.py`
- [ ] **A5. Frontend visual** `static/`
  - [ ] Tablero SVG 9×9 interactivo (clic para colocar)
  - [ ] Modos: PvP, humano vs IA, IA vs IA
  - [ ] Controles: colocar, pasar, rendirse, nueva partida, selector de simulaciones, selector de versión de IA
  - [ ] Panel en vivo: turno, capturas, puntuación, sims, nodos, tiempo de decisión, win-rate estimado
- [ ] **A6. Replay** `static/js/replay.js`
  - [ ] Velocidad ajustable, anterior/siguiente, saltar al movimiento N
  - [ ] Mostrar coordenadas y métricas por movimiento
  - [ ] Comparar decisiones de la IA durante la partida
  - [ ] Reconstrucción re-aplicando coordenadas del JSON
- [ ] **A7. Métricas de app + dashboard** `static/js/metrics.js`
  - [ ] `GET /api/perf` con latencias, memoria, tiempos de IA
  - [ ] Dashboard con Chart.js: rankings, win-rates, tiempos de decisión, distribución de latencias

### Fase B — IA inspirada en AlphaGo

- [x] **B8. Dataset histórico** `training/download_dataset.py` + `training/dataset.py`
  - [x] Descarga de SGF públicos 9×9 → `data/historical/` (fuentes configurables; usa directamente los `.sgf` presentes)
  - [x] Parser SGF → posiciones codificadas (color, turno, legales) + etiquetas (movimiento realizado / resultado) + compatibilidad 19×19
- [x] **B9. Redes** `training/nets.py`
  - [x] CNN pequeña (3 capas conv 3×3, BN, ReLU), entrada multicanal (5 canales, coincide con `ai/redes.py`)
  - [x] Policy: logits de 82 (81 intersecciones + 1 pase)
  - [x] Value: sigmoide (probabilidad de ganar)
  - [x] Export a ONNX (`policy.onnx` + `value.onnx`, batch dinámico; tests con `importorskip`)
- [ ] **B10. Notebook Colab** `training/Colab_AlphaGo.ipynb`
  - [x] Carga de dataset (SGF → muestras, split train/val)
  - [x] Definición de redes (`training/nets.py`)
  - [x] Entrenamiento Policy + Value (loss combinado)
  - [x] Export `.onnx` → copiar a `models/` + verificación con `cargar_redes`
  - [ ] Self-play v1 → v3 (guiones listos; ejecución en Colab)
- [ ] **B11. Integración MCTS + redes** `ai/mcts.py` + `ai/redes.py`
  - [x] Policy guía la selección (priors PUCT) y expansión
  - [x] Value evalúa nodos hoja
  - [x] Inferencia vía ONNX Runtime (`ai/redes.py`, ONNX opcional en runtime)
  - [x] Fallback elegante si no hay modelos (baseline heurístico)
  - [ ] Modelos entrenados reales en `models/`
- [ ] **B12. Experimento 2** endpoint `/api/ai/experiment` + `ai/experimento.py`
  - [x] Harness: configs `aleatorio`, `mcts-<sims>`, `mcts-<sims>+red`; partidas con semilla
  - [x] Agrega victorias, empates, movimientos y tiempos promedio por jugador
  - [x] MCTS heurístico vs MCTS + Policy + Value
  - [x] Medir win-rate, tiempo por movimiento, rendimiento general
  - [ ] Comparativas formales publicadas (ver D17)

### Fase C — Self-play (evolución de modelos)

- [ ] **C13. Self-play** `training/self_play.py`
  - [x] IA vs IA (con modelo/config actual): generador de SGF con callback `al_jugar`
  - [x] Guardar partidas en `data/training/` y/o `data/historical/`
  - [ ] Reentrenamiento → v2, v3
- [ ] **C14. Meta-modelos** `data/models_meta.json`
  - [x] `models_meta.json` creado (esquema; sin versiones hasta tener modelos)
  - [ ] Versionar modelos y resultados
  - [ ] Gráficos de evolución v1 → v3 en el dashboard
- [ ] **C15. Experimento 3**
  - [x] Cada versión vs aleatoria, vs baseline heurístico, vs versión anterior (mediante `ai/experimento.py`)
  - [ ] Resultados agregados en el dashboard

### Fase D — Análisis de desempeño

- [ ] **D16. Modo análisis de posición**
  - [x] Cargar cualquier posición guardada
  - [x] Pedir top jugadas a la IA con win-rate
- [x] **D17. Informe de desempeño** `analysis/performance_report.py`
  - [x] Genera `performance_report.md` y `performance_report.html` (datos en vivo del servidor o disco)
  - [x] Secciones: arquitectura, configuración experimental, rendimiento del motor (benchmark), latencia de la app, rendimiento del MCTS, impacto de simulaciones, estado de las redes, baseline vs redes, evolución de modelos, tiempo/memoria, experimentos, conclusiones y limitaciones
  - [ ] Curar el informe tras la integración de modelos (`--experimentos`)
- [ ] **D18. Verificación final**
  - [x] `pytest` completo (engine, mcts, api, dataset, self-play, redes skip, informe)
  - [ ] Curar informe con datos reales tras iteración de modelos

---

## Configuración experimental

- **Experimento 1 — MCTS baseline:** 250 vs 800 vs 2000 simulaciones (medir tiempo, nodos, win-rate).
- **Experimento 2 — Baseline vs MCTS+redes:** win-rate, tiempo por movimiento, rendimiento general.
- **Experimento 3 — Evolución self-play:** v1 vs v2 vs v3, cada versión contra aleatoria, MCTS heurístico y versión anterior.

## Convención de código

**Todo el código en español**: nombres de funciones, variables, clases, comentarios, mensajes de error y de UI. Ejemplos: `colocar_piedra()`, `calcular_libertades`, `jugar_movimiento()`, `Tablero`, `partida`, `turno`, `capturas`, `puntaje`. Los identificadores técnicos (ONNX, JSON, API, MCTS, SGF) se conservan en inglés por ser nombres propios de librerías/protocolos.

## Restricciones ambientales / cómo ejecutar

- Backend: `pip install -r requirements.txt` con `flask` y `onnxruntime` (CPU).
- Módulo de python para rutas: usar rutas absolutas/relativas al repo base (todas las operaciones de archivo relativas al workspace).
- Cheats: `pytest tests/` desde la raíz del proyecto.

## Notas de diseño (pendientes durante implementación)

- Superko: v1 ko simple; opcional.
- Dataset: si el download público falla, el parser acepta cualquier SGF colocado en `data/historical/`.
- Redes: entrada 3–8 canales; policy softmax 82; value sigmoide.
- `models_meta.json` permite varias versiones de modelo para comparación en vivo.