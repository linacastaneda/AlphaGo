"""Módulo de IA: MCTS con UCT y playouts heurísticos."""

from .mcts import MCTS, Nodo
from .rollout import elegir_movimiento_heurístico, simular_partida

__all__ = ["MCTS", "Nodo", "elegir_movimiento_heurístico", "simular_partida"]