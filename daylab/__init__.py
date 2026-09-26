"""Deterministic daytime PvZ experiments. Importing this package has no UI effects."""

from .config import ExperimentConfig

__all__ = ["ExperimentConfig", "GameSession"]


def __getattr__(name):
    if name == "GameSession":
        from .session import GameSession

        return GameSession
    raise AttributeError(name)
