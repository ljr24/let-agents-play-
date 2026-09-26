"""UI facade, keeping existing imports stable while separating responsibilities."""
from .input import InputRouter
from .view import GameView
from .play import play
from .replay_view import replay_window
from .launcher import launcher

__all__ = ["InputRouter", "GameView", "play", "replay_window", "launcher"]
