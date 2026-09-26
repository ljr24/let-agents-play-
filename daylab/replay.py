"""Replay from tick zero with saved inputs and environment, never call a model."""
import json
from pathlib import Path

from .config import ExperimentConfig
from .recording import read_lines, fingerprint, digest, first_difference
from .session import GameSession
from .schemas import validate_manifest


class ReplayPlayer:
    def __init__(self, directory, *, headless=True, allow_version_mismatch=False):
        self.directory = Path(directory)
        self.manifest = validate_manifest(
            json.loads((self.directory / "manifest.json").read_text(encoding="utf-8"))
        )
        result_path = self.directory / "result.json"
        self.result = (
            json.loads(result_path.read_text(encoding="utf-8")) if result_path.exists() else {}
        )
        current = fingerprint()
        self.version_differences = {
            k: {"recorded": v, "current": current.get(k)}
            for k, v in self.manifest["versions"].items()
            if current.get(k) != v
        }
        if self.version_differences and not allow_version_mismatch:
            raise ValueError("Replay version mismatch: " + ", ".join(self.version_differences))
        self.submissions = read_lines(self.directory / "submissions.jsonl")
        self.checkpoints = {
            item["tick"]: item for item in read_lines(self.directory / "checkpoints.jsonl")
        }
        self.last_tick = self.result.get("tick", max(self.checkpoints, default=0))
        self.headless = headless
        self.session = None
        self.restart()

    def restart(self):
        if self.session:
            self.session.close("replay_restart")
        self.session = GameSession(headless=self.headless, record=False)
        self.session.reset(
            ExperimentConfig.from_dict(self.manifest["config"]),
            self.manifest["seed"],
            schedule=self.manifest["schedule"],
        )
        self.index = self.verified = 0
        self.difference = None
        if self.last_tick == 0:
            self._final_boundary()
        self._check()

    def _check(self):
        if self.difference:
            return
        expected = self.checkpoints.get(self.session.tick)
        if expected:
            actual = self.session.internal_state()
            if digest(actual) != expected["hash"]:
                self.difference = {
                    "tick": self.session.tick,
                    "sim_ms": self.session.ms,
                    "field": first_difference(expected["state"], actual),
                }
            else:
                self.verified += 1

    def _submit_current(self):
        while (
            self.index < len(self.submissions)
            and self.submissions[self.index]["tick"] == self.session.tick
        ):
            item = self.submissions[self.index]
            tick = item["observation_tick"]
            obs_id = f"{self.session.episode_id}:{tick}" if tick is not None else "invalid"
            actual = self.session.submit(item["action"], obs_id, item["command_id"])
            if actual != item["receipt"]:
                self.difference = {
                    "tick": self.session.tick,
                    "sim_ms": self.session.ms,
                    "field": first_difference(item["receipt"], actual, "$.receipt"),
                }
                return False
            self.index += 1
        return True

    def _final_boundary(self):
        self._submit_current()
        if self.session.status == "running":
            saved_status = self.result.get("status", "interrupted")
            if saved_status != "running":
                self.session.finish(saved_status)
                self.session._publish()

    def step(self):
        if self.difference or self.session.tick >= self.last_tick:
            return False
        if not self._submit_current():
            return False
        if self.session.status != "running":
            self.difference = {
                "tick": self.session.tick,
                "sim_ms": self.session.ms,
                "field": {"path": "$.status", "actual": "ended before saved final tick"},
            }
            return False
        self.session.advance()
        if self.session.tick == self.last_tick:
            self._final_boundary()
        self._check()
        return self.difference is None

    def seek(self, sim_ms):
        target = min(self.last_tick, max(0, int(sim_ms) // 20))
        if target < self.session.tick:
            self.restart()
        while self.session.tick < target and self.step():
            pass
        return self.session.observe()

    def verify(self):
        self.seek(self.last_tick * 20)
        coverage = self.last_tick in self.checkpoints and self.index == len(self.submissions)
        return {
            "verified": self.difference is None and not self.version_differences and coverage,
            "state_match": self.difference is None and coverage,
            "checkpoint_count": self.verified,
            "last_tick": self.session.tick,
            "complete_coverage": coverage,
            "first_difference": self.difference,
            "version_differences": self.version_differences,
            "recording_finalized": self.result.get("finalized", False),
        }

    def close(self):
        self.session.close("replay_closed")


def verify_replay(directory, **kwargs):
    player = ReplayPlayer(directory, **kwargs)
    try:
        return player.verify()
    finally:
        player.close()
