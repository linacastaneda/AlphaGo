# AlphaGo – Implementación de Go con MCTS

## Integrantes

- **Lina María Castañeda Hernández**
- **Jorge Antonio García Romero**

## Descripción del proyecto

Este proyecto desarrolla una aplicación capaz de jugar **Go**, inspirada en los conceptos presentados en el documental *AlphaGo*.

El objetivo principal es implementar una aplicación que pueda jugar GO usando las reglas fundamentales del juego y  simular alphaGo en este usando solo **Monte Carlo Tree Search (MCTS)** sin redes neuronales de política (propone un movimiento) y valor (calcula el valor futuro de quedar en esa posición) tal y como es el AlphaGo.

---

# 1. Estructura del proyecto

```text
AlphaGo/
│
├── README.md
│
└── backend/
    ├── motor_go.py
    ├── ia_go.py
    ├── test_go.py
    ├── test_ia.py
    ├── benchmark.py
    └── graficas.py
```

### `motor_go.py`

Contiene la lógica principal del juego de Go:

- Creación del tablero.
- Colocación de piedras.
- Alternancia de turnos.
- Detección de vecinos.
- Identificación de grupos.
- Cálculo de libertades.
- Captura de piedras.
- Prevención de suicidio.
- Regla de Ko.
- Pase de turno.
- Finalización por dos pases consecutivos.
- Generación de movimientos válidos.
- Copia del estado del juego.
- Cálculo de puntuación.

### `ia_go.py`

Implementa el agente de inteligencia artificial mediante **Monte Carlo Tree Search (MCTS)**.

### `test_go.py`

Contiene las pruebas unitarias correspondientes al motor y las reglas del juego.

### `test_ia.py`

Contiene pruebas para verificar el comportamiento básico de la inteligencia artificial, es decir el uso de MCTS.

### `benchmark.py`

Ejecuta partidas experimentales entre la IA MCTS y un jugador que selecciona movimientos legales aleatoriamente.

### `graficas.py`

Genera las visualizaciones utilizadas para analizar los resultados obtenidos en el benchmark.

---

# 2. Motor de Go

El tablero se representa mediante una matriz cuadrada.

Se utilizan los siguientes valores:

```python
VACIO = 0
NEGRA = 1
BLANCA = -1
```

Por defecto, el motor puede trabajar con un tablero de 9×9, aunque para las pruebas de desempeño se utilizó un tablero reducido de **5×5** con el objetivo de disminuir el costo computacional de los experimentos.

Una de las partes fundamentales de la implementación consiste en determinar las **libertades** de las piedras.

En Go, una piedra o grupo permanece en el tablero mientras tenga al menos una intersección vacía adyacente. Cuando un grupo pierde todas sus libertades, es capturado y retirado del tablero.

El motor también verifica que una jugada sea válida antes de modificar permanentemente el estado de la partida.

---

# 3. Inteligencia Artificial

La inteligencia artificial utiliza **Monte Carlo Tree Search (MCTS)**.

MCTS permite analizar posibles decisiones construyendo progresivamente un árbol de búsqueda y realizando simulaciones de partidas.

Cada iteración está compuesta por cuatro etapas principales.

## 3.1 Selección

El algoritmo recorre el árbol existente seleccionando los nodos más prometedores usando UCT

Para equilibrar la exploración de nuevas posibilidades y el aprovechamiento de movimientos que anteriormente obtuvieron buenos resultados, se utiliza el criterio **UCT (Upper Confidence Bound applied to Trees)** este se encarga de calcular un puntaje para cada nodo hijo y elige el que tenga valor mas alto haciendo uso de una ecuación que se compone por el termino de **explotación** que es la rentabilidad, en este caso # de victorias pasando por el nodo y sobre numero de veces que el nodo ha sido visitado (tasa de victorias del nodo) y de **Exploración** que mide que tan "ignorado" esta el nodo, con estas dos escoge el camino a seguir.

## 3.2 Expansión

Cuando se encuentra un nodo que todavía contiene movimientos sin explorar, se selecciona uno de ellos y se crea un nuevo nodo en el árbol.

El pase de turno también se considera una acción posible.

## 3.3 Simulación

Desde el nuevo estado se ejecuta una partida simulada mediante movimientos aleatorios.

La simulación continúa hasta que:

- ambos jugadores pasan consecutivamente, o
- se alcanza un límite máximo de movimientos.

Posteriormente se calcula la puntuación del tablero para determinar el ganador de la simulación.

## 3.4 Retropropagación

El resultado obtenido durante la simulación se propaga desde el nodo explorado hasta la raíz.

Cada nodo registra:

- número de visitas;
- número de victorias;
- movimiento realizado;
- jugador que realizó el movimiento.

Esto permite evaluar los resultados desde la perspectiva correspondiente a cada jugador.

---

# 4. Pruebas

Se implementaron pruebas unitarias para verificar el comportamiento

Las pruebas del motor comprueban, entre otros aspectos:

- inicialización correcta del tablero;
- movimientos válidos;
- alternancia de turnos;
- movimientos fuera de los límites;
- casillas ocupadas;
- vecinos;
- libertades;
- grupos;
- capturas;
- regla de no suicidio;
- regla de Ko;
- pases y finalización de la partida.

Las pruebas de la IA verifican que:

- pueda seleccionar acciones;
- seleccione movimientos legales;
- no juegue sobre posiciones ocupadas;
- la búsqueda MCTS no modifique el tablero real mientras analiza;
- los movimientos seleccionados puedan ser ejecutados por el motor.

---

# 5. Evaluación del desempeño

Para analizar el comportamiento se desarrolló un benchmark que enfrenta el agente MCTS contra un jugador que selecciona movimientos legales de manera aleatoria.

El experimento se realizó sobre un tablero **5×5**.

Se probaron cuatro configuraciones:

- 10 simulaciones MCTS.
- 25 simulaciones MCTS.
- 50 simulaciones MCTS.
- 100 simulaciones MCTS.

En cada configuración se ejecutaron **10 partidas**, alternando el color de la IA entre negras y blancas para reducir el efecto de jugar siempre en la misma posición de turno.

Las métricas utilizadas fueron:

- victorias;
- derrotas;
- empates;
- porcentaje de victorias;
- tiempo promedio de decisión por jugada;
- número promedio de movimientos por partida.

---

# 6. Resultados experimentales

Los resultados obtenidos en la ejecución analizada fueron:

| Simulaciones MCTS | Victorias | Derrotas | Empates | Porcentaje de victoria | Tiempo promedio/jugada | Movimientos promedio |
|---:|---:|---:|---:|---:|---:|---:|
| 10 | 9 | 1 | 0 | 90 % | 0.0500 s | 50.3 |
| 25 | 9 | 1 | 0 | 90 % | 0.1134 s | 63.1 |
| 50 | 8 | 2 | 0 | 80 % | 0.2572 s | 46.7 |
| 100 | 10 | 0 | 0 | 100 % | 0.5121 s | 46.1 |

![captura ejecución](Ejecucion_Benchmark.png)
---

# 7. Análisis de efectividad

La siguiente gráfica muestra el porcentaje de victorias obtenido por cada configuración.

![Efectividad de MCTS](mcts_winrate.png)

En la muestra evaluada, todas las configuraciones alcanzaron porcentajes de victoria iguales o superiores al **80 %** frente al jugador aleatorio.

Los resultados fueron:

- 10 simulaciones: **90 %**
- 25 simulaciones: **90 %**
- 50 simulaciones: **80 %**
- 100 simulaciones: **100 %**

La configuración de 100 simulaciones obtuvo el mejor resultado de esta ejecución, ganando las 10 partidas realizadas.

Sin embargo, el porcentaje de victorias no aumentó de forma estrictamente progresiva. La configuración de 50 simulaciones obtuvo un resultado inferior a las configuraciones de 10 y 25 simulaciones.

Esto no permite concluir que 50 simulaciones sean necesariamente peores. MCTS contiene componentes estocásticos(aleatorios) y el oponente utilizado en el benchmark también selecciona movimientos aleatoriamente. Adicionalmente, una muestra de 10 partidas por configuración produce una variabilidad considerable: una sola partida representa 10 puntos porcentuales del resultado.


---

# 8. Costo computacional

![Costo computacional de MCTS](mcts_tiempo.png)

El efecto más claro observado durante el experimento corresponde al incremento del costo computacional.

Los tiempos promedio fueron:

| Simulaciones | Tiempo promedio por jugada |
|---:|---:|
| 10 | 0.0500 s |
| 25 | 0.1134 s |
| 50 | 0.2572 s |
| 100 | 0.5121 s |

Al pasar de 10 a 100 simulaciones, la cantidad de simulaciones aumenta **10 veces**, mientras que el tiempo promedio pasa de aproximadamente **0.05 a 0.51 segundos por decisión**.

Esto representa un incremento aproximado de **10.2 veces** en el tiempo de procesamiento.

Por lo tanto, en las condiciones de este experimento se observa una relación aproximadamente lineal entre el número de simulaciones MCTS y el costo temporal de la toma de decisiones.

---

# 9. Duración de las partidas

![Duración de las partidas](mcts_movimientos.png)

También se analizó el número promedio de movimientos realizados durante las partidas.

Los resultados fueron:

- 10 simulaciones: 50.3 movimientos.
- 25 simulaciones: 63.1 movimientos.
- 50 simulaciones: 46.7 movimientos.
- 100 simulaciones: 46.1 movimientos.

No se observa una relación estrictamente lineal entre el número de simulaciones y la duración de la partida.

La configuración de 25 simulaciones produjo las partidas más largas, mientras que las configuraciones de 50 y 100 simulaciones presentaron valores similares y menores.

Debido al carácter aleatorio del adversario y de las simulaciones, esta métrica debe considerarse secundaria y requeriría un número mayor de partidas para establecer una tendencia.


---

# 11. Variabilidad experimental

MCTS es un algoritmo con componentes aleatorios.

Durante la expansión y simulación pueden seleccionarse diferentes movimientos en ejecuciones distintas. El adversario utilizado para el benchmark también utiliza una estrategia aleatoria.

Como consecuencia, ejecutar nuevamente el mismo experimento puede producir porcentajes de victoria diferentes.

---

# 12. Relación con AlphaGo

El documental *AlphaGo* muestra cómo el juego de Go representa un desafío significativo para la inteligencia artificial debido a la enorme cantidad de posibles configuraciones del tablero.

La implementación realizada en este proyecto utiliza **Monte Carlo Tree Search**, uno de los componentes fundamentales asociados al enfoque utilizado por AlphaGo.

Sin embargo, existen diferencias importantes.

Esta aplicación utiliza:

- MCTS.
- UCT para selección.
- simulaciones aleatorias.
- un motor propio para validar las reglas de Go.

---

# 13. Conclusiones

La implementación permitió desarrollar un motor funcional de Go y un agente capaz de seleccionar movimientos mediante Monte Carlo Tree Search.

Las pruebas unitarias permitieron verificar las principales reglas del juego y comprobar que la IA puede analizar movimientos sin modificar accidentalmente el estado real de la partida.

Los experimentos muestran que el agente MCTS logra superar con frecuencia a un jugador aleatorio en un tablero reducido de 5×5.

El resultado más consistente del benchmark corresponde al costo computacional: aumentar la cantidad de simulaciones incrementa aproximadamente de manera proporcional el tiempo necesario para seleccionar una jugada.

En términos de efectividad, una mayor cantidad de simulaciones permite realizar una búsqueda más extensa, pero los resultados presentan variabilidad debido a los componentes aleatorios del algoritmo y al tamaño reducido de la muestra.

En la ejecución analizada, la configuración de 100 simulaciones obtuvo 10 victorias en 10 partidas, aunque necesitó aproximadamente 0.51 segundos por decisión. En contraste, la configuración de 10 simulaciones obtuvo 9 victorias en 10 partidas utilizando aproximadamente 0.05 segundos por jugada.

---

# 14. Ejecución

## Ejecutar las pruebas del motor

```bash
python backend/test_go.py
```

## Ejecutar las pruebas de la IA

```bash
python backend/test_ia.py
```

## Ejecutar el benchmark

```bash
python backend/benchmark.py
```

---
