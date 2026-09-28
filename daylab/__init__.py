"""Deterministic daytime PvZ experiments. Importing this package has no UI effects."""

from .config import ExperimentConfig
from .benchmark import load_benchmark

__all__ = ["ExperimentConfig", "GameSession", "load_benchmark"]


def __getattr__(name):
    if name == "GameSession":
        from .session import GameSession

        return GameSession
    raise AttributeError(name)
