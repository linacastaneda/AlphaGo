"""IA de Lina integrada en nuestro código: MCTS académico portado.

Reemplaza al adaptador anterior que dependía de ``backend/ia_go``.
Ahora usa ``ai.mcts_lina.MCTSLina``, que juega con nuestro motor y respeta
el límite de tiempo de forma nativa (sin calibración por jugada).

En duelos se aplica un handicap: ``HANDICAP_LINA`` multiplica las
simulaciones efectivas, porque su rollout aleatorio puro es más débil
que nuestro rollout heurístico a igualdad de simulaciones.
"""

from .mcts_lina import MCTSLina

HANDICAP_LINA = 3


def es_config_lina(config: str) -> bool:
    return isinstance(config, str) and config.startswith("lina-")


def sims_efectivos(config: str) -> int:
    """Simulaciones reales que usará Lina (aplicando el handicap)."""
    base = int(config.split("-")[1])
    return base * HANDICAP_LINA


def config_reporte(simulaciones: int) -> str:
    return f"lina-{simulaciones}"


class RivalLina:
    """Envuelve a ``MCTSLina`` con la misma interfaz que ``MCTS``."""

    def __init__(self, simulaciones: int, tiempo_limite_ms: int | None = None,
                 handicap: int = HANDICAP_LINA):
        self.simulaciones_base = simulaciones
        self.handicap = handicap
        self.tiempo_limite_ms = tiempo_limite_ms
        self.simulaciones = simulaciones * handicap
        self._mcts = MCTSLina(simulaciones=self.simulaciones,
                              tiempo_limite_ms=tiempo_limite_ms)

    def _nombre_config(self) -> str:
        return config_reporte(self.simulaciones)

    def mejor_jugada(self, partida) -> dict:
        resultado = self._mcts.mejor_jugada(partida)
        resultado["config"] = self._nombre_config()
        return resultado

    def analizar(self, partida, n: int = 5) -> dict:
        resultado = self._mcts.analizar(partida, n=n)
        resultado["config"] = self._nombre_config()
        return resultado


def crear_rival(simulaciones: int = 250, tiempo_limite_ms: int | None = None,
                handicap: int = HANDICAP_LINA) -> RivalLina:
    """Factoría: IA de Lina con handicap aplicado sobre las simulaciones."""
    return RivalLina(simulaciones=simulaciones,
                     tiempo_limite_ms=tiempo_limite_ms, handicap=handicap)
