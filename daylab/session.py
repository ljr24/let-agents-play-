"""Local, single-writer experiment API. Only this module commits actions/resources."""
from collections import deque
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import random
import threading
import time
import uuid

from .config import ExperimentConfig, rules_text
from .scenarios import make_schedule
from .economy import ResourceLedger
from .schemas import APP_VERSION, MANIFEST_VERSION, STREAM_VERSIONS
from .recording import Recorder, ROOT, clean, digest, fingerprint
from .run_store import identity, run_directory


class GameSession:
    def __init__(
        self, *, headless=True, realtime=False, output_root=ROOT / "experiments", record=True,
        execution_mode=None
    ):
        self.headless, self.realtime = headless, realtime
        self.execution_mode = execution_mode or ('realtime' if realtime else 'offline')
        if self.execution_mode not in ('realtime', 'offline', 'pause_think') or (self.execution_mode == 'pause_think' and realtime):
            raise ValueError('Invalid execution mode')
        self.output_root, self.record = Path(output_root), record
        self.owner_thread = threading.get_ident()
        self.recorder = None
        self.closed = True

    def _owner(self):
        if threading.get_ident() != self.owner_thread:
            raise RuntimeError("Game state belongs to the creating thread")

    def reset(self, config=None, seed=0, *, schedule=None):
        self._owner()
        if not self.closed:
            self.close("reset")
        self.config = ExperimentConfig.from_dict(
            config.to_dict() if isinstance(config, ExperimentConfig) else config or {}
        )
        if type(seed) is not int:
            raise ValueError("seed must be an integer")
        self.seed = seed
        self.schedule = (
            deepcopy(schedule) if schedule is not None else make_schedule(self.config, seed)
        )
        self._validate_schedule()
        from game import assets as tool

        tool.initialize(
            headless=self.headless,
            muted=self.headless,
            size=(800, 600) if self.headless else (800, 700),
        )
        from game.world import Battlefield

        self.episode_id = uuid.uuid4().hex
        self.tick = self.ms = self.seq = self.entity_counter = self.schedule_index = self.wave = 0
        self.economy = ResourceLedger(self.config)
        self.next_natural_sun = 7000
        self.game_rng = random.Random(seed ^ 0xA11CE)
        self.visual_rng = random.Random(seed ^ 0xD15A1A7)
        self.entities, self.commands, self.command_payloads = {}, {}, {}
        self.queue, self.pending_sun, self.event_log = deque(), [], []
        self.history, self.public_actions = deque(), deque()
        self.observation_cache = {}
        self.last_submit_ms = -self.config.action_interval_ms
        self.source_id = None
        self.status = "running"
        self.flags = []
        self.started_wall = time.monotonic()
        self.closed = False
        self.directory = None
        self.recorder = None
        if self.record:
            self.directory = run_directory(self.output_root, self.config, seed, self.episode_id)
            self.recorder = Recorder(
                self.directory,
                {
                    "schema_version": MANIFEST_VERSION,
                    "app_version": APP_VERSION,
                    "stream_versions": STREAM_VERSIONS,
                    "episode_id": self.episode_id,
                    "run_identity": identity(self.config),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "config": self.config.to_dict(),
                    "seed": seed,
                    "schedule": self.schedule,
                    "environment_id": self.environment_id(),
                    "condition_id": self.condition_id(),
                    "config_revision": digest(
                        {
                            k: v
                            for k, v in self.config.to_dict().items()
                            if k not in ("actor", "practice", "level_id", "scheme_id")
                        }
                    ),
                    "versions": fingerprint(),
                    "realtime": self.realtime,
                    "execution_mode": self.execution_mode,
                    "rules": rules_text(self.config),
                    "public_history_sample_ms": 1000,
                    "timing_policy": {"lag_threshold_ms": 500, "sustained_lag_ms": 2000},
                },
            )
        self.level = Battlefield(self)
        from .actions import ActionExecutor

        self.actions = ActionExecutor(self)
        self._publish()
        self.checkpoint()
        return self.observe()

    def _validate_schedule(self):
        last = -1
        for event in self.schedule:
            if set(event) != {"at_ms", "wave", "type", "row", "x"}:
                raise ValueError("Invalid environment event")
            if (
                event["type"] not in self.config.enabled_zombies
                or type(event["row"]) is not int
                or not 0 <= event["row"] < 5
                or type(event["at_ms"]) is not int
                or event["at_ms"] < last
                or event["at_ms"] < 0
                or event["at_ms"] % 20
                or type(event["wave"]) is not int
                or not 1 <= event["wave"] <= 100
                or type(event["x"]) is not int
                or event["x"] != 830
            ):
                raise ValueError("Invalid/disabled environment event")
            last = event["at_ms"]

    def environment_id(self):
        config = self.config.to_dict()
        for key in ("actor", "practice", "level_id", "scheme_id", "enabled_plants", "plant_overrides"):
            config.pop(key, None)
        return digest({"config": config, "schedule": self.schedule})

    def condition_id(self):
        config = self.config.to_dict()
        for key in ("actor", "practice", "level_id", "scheme_id"):
            config.pop(key, None)
        return digest({"config": config, "schedule": self.schedule})

    def log(self, name, value):
        if self.recorder:
            self.recorder.append(
                name, {"tick": self.tick, "sim_ms": self.ms, "event_seq": self.seq, **value}
            )

    def emit(self, event_type, **data):
        self.seq += 1
        event = clean(dict(seq=self.seq, tick=self.tick, sim_ms=self.ms, type=event_type, **data))
        self.event_log.append(event)
        if self.recorder:
            self.recorder.append("events", event)
        return event

    def register(self, obj, kind, row):
        self.entity_counter += 1
        if kind in ("bullet", "visual"):
            obj.current_time = obj.animate_timer = self.ms
            source = self.entities.get(self.source_id)
            if row is None and source:
                row = source.lab_row
        obj.lab_id = f"{kind}-{self.entity_counter:05d}"
        obj.lab, obj.lab_kind, obj.lab_row = self, kind, row
        obj.lab_owner = getattr(obj, "lab_owner", self.source_id) if kind in ("bullet", "visual") else None
        obj.lab_removed = obj.lab_death_reported = False
        self.entities[obj.lab_id] = obj
        self.emit(
            kind + "_created",
            entity_id=obj.lab_id,
            entity_type=getattr(obj, "name", kind),
            row=row,
            col=getattr(obj, "lab_col", None),
            owner_id=obj.lab_owner,
        )

    def damage(self, obj, before, source_id, reason="attack"):
        from game.tracking import health

        after = health(obj)
        if after == before:
            return
        obj.lab_last_damage_source = source_id
        source = self.entities.get(source_id)
        self.emit(
            "damage",
            target_id=obj.lab_id,
            source_id=source_id,
            before=before,
            after=after,
            reason=reason,
            owner_id=getattr(source, "lab_owner", None),
            modifier_ids=getattr(source, "lab_modifiers", []),
            base_damage=getattr(source, "lab_base_damage", None),
            projectile_damage=getattr(source, "damage", None),
        )
        for key in ("helmet_health", "helmet_type2_health"):
            if before[key] > 0 and after[key] <= 0:
                self.emit("armor_broken", target_id=obj.lab_id, armor=key, source_id=source_id)
        if before["health"] > 0 and after["health"] <= 0:
            self.emit("health_depleted", target_id=obj.lab_id, source_id=source_id)

    def audit_death(self, obj):
        from game import constants as c

        if obj.state == c.DIE and not obj.lab_death_reported:
            obj.lab_death_reported = True
            self.emit(
                "zombie_death",
                zombie_id=obj.lab_id,
                zombie_type=obj.name,
                source_id=getattr(obj, "lab_last_damage_source", None),
            )

    def removed(self, obj):
        if obj.lab_removed:
            return
        if obj.lab_kind == "zombie":
            self.audit_death(obj)
        obj.lab_removed = True
        if obj.lab_kind == "plant":
            self.level.on_plant_removed(obj)
        self.emit(
            "entity_removed",
            entity_id=obj.lab_id,
            kind=obj.lab_kind,
            reason=getattr(obj, "lab_remove_reason", "animation_or_exit"),
        )

    def observe(self):
        self._owner()
        return deepcopy(self.observation)

    def public_context(self, observation=None):
        obs = observation or self.observe()
        end = obs["sim_ms"]
        return {
            "rules": rules_text(self.config),
            "observation": obs,
            "history": [
                deepcopy(o)
                for o in self.history
                if end - 5000 <= o["sim_ms"] < end and o["sim_ms"] % 1000 == 0
            ],
            "past_actions": [
                deepcopy(a) for a in self.public_actions if end - 5000 <= a["sim_ms"] <= end
            ],
        }

    def submit(self, action, observation_id, command_id):
        return self.actions.submit(action, observation_id, command_id)

    def _credit(self, source, amount):
        actual = self.economy.credit(amount)
        self.emit("sun_income", source_id=source, produced=amount, amount=actual, balance=self.sun)

    def _tick(self):
        self._owner()
        if self.closed or self.status != "running":
            return
        self.tick += 1
        self.ms = self.tick * 20
        while self.queue:
            self.actions.execute(self.queue.popleft())
        while (
            self.schedule_index < len(self.schedule)
            and self.schedule[self.schedule_index]["at_ms"] <= self.ms
        ):
            event = self.schedule[self.schedule_index]
            if event["wave"] != self.wave:
                self.wave = event["wave"]
                self.emit("wave_started", wave=self.wave)
            self.level.spawn(event)
            self.schedule_index += 1
        self.level.update_entities()
        self.level.collisions()
        if self.ms >= self.next_natural_sun:
            self.pending_sun.insert(0, ("environment", 25))
            self.next_natural_sun += 7000
        for source, amount in self.pending_sun:
            self._credit(source, amount)
        self.pending_sun.clear()
        if self.level.checkLose():
            self.finish("defeat")
        elif self.schedule_index == len(self.schedule) and not any(self.level.zombie_groups):
            self.finish("victory")
        elif self.ms >= self.config.max_time_ms:
            self.finish("timeout")
        self._publish()
        if self.tick % 50 == 0 or self.status != "running":
            self.checkpoint()

    def advance(self, ticks=1):
        self._owner()
        if self.realtime:
            raise RuntimeError("advance is only available for offline testing/replay")
        if type(ticks) is not int or ticks < 0:
            raise ValueError("ticks must be a nonnegative integer")
        for _ in range(ticks):
            if self.closed or self.status != "running":
                break
            self._tick()
        return self.observe()

    def step_realtime(self):
        """Host runner only. Controllers must not call clock advancement."""
        if not self.realtime:
            raise RuntimeError("Use advance() for offline sessions")
        self._tick()

    def cell_at(self, scene_x, scene_y):
        """Convert scene coordinates to a valid (row, col), without exposing map objects."""
        col, row = self.level.map.getMapIndex(scene_x, scene_y)
        return (row, col) if 0 <= row < 5 and 0 <= col < 9 else None

    def render_scene(self, surface):
        self.level.draw(surface)

    @property
    def sun(self):
        return self.economy.sun

    @sun.setter
    def sun(self, value):
        self.economy.sun = value  # Internal test compatibility; controllers use submit().

    @property
    def cooldowns(self):
        return self.economy.cooldowns

    @property
    def prices(self):
        return self.economy.prices

    @property
    def cooldown_lengths(self):
        return self.economy.cooldown_lengths

    def _publish(self):
        from .observation import build_observation

        self.observation = build_observation(self)
        self.observation_cache[self.tick] = self.observation
        while self.observation_cache and next(iter(self.observation_cache)) * 20 < self.ms - self.config.max_observation_age_ms:
            del self.observation_cache[next(iter(self.observation_cache))]
        if self.tick % 5 == 0 or self.status != "running":
            self.history.append(deepcopy(self.observation))
            self.log("observations", {"observation": self.observation})
        while self.history and self.history[0]["sim_ms"] < self.ms - 5000:
            self.history.popleft()
        while self.public_actions and self.public_actions[0]["sim_ms"] < self.ms - 5000:
            self.public_actions.popleft()
        if self.tick % 250 == 0 and self.status == "running":
            self.log("wait_samples", {"input": self.public_context(), "action": {"type": "WAIT"}})

    def events(self, after_seq=0):
        self._owner()
        return deepcopy([e for e in self.event_log if e["seq"] > after_seq])

    def internal_state(self):
        from .state_codec import build_checkpoint

        return build_checkpoint(self)

    def checkpoint(self):
        state = self.internal_state()
        self.log("checkpoints", {"hash": digest(state), "state": state})
        self._save_result()
        return digest(state)

    def flag(self, reason, **details):
        if reason not in self.flags:
            self.flags.append(reason)
        self.emit(
            "intervention" if reason != "timing_anomaly" else "timing_anomaly",
            reason=reason,
            **details,
        )

    def finish(self, status):
        if self.status != "running":
            return
        self.status = status
        self.emit("episode_ended", result=status)

    def _save_result(self):
        if self.recorder:
            self.recorder.write_json(
                "result.json",
                dict(
                    status=self.status,
                    tick=self.tick,
                    sim_ms=self.ms,
                    flags=self.flags,
                    finalized=self.closed,
                    environment_id=self.environment_id(),
                    actor=self.config.actor,
                    practice=self.config.practice,
                    comparison_eligible=self.closed
                    and self.status in ("victory", "defeat", "timeout")
                    and not self.flags
                    and not self.config.practice,
                    wall_elapsed_ms=round((time.monotonic() - self.started_wall) * 1000),
                    execution_mode=self.execution_mode,
                ),
            )

    def close(self, reason="closed"):
        self._owner()
        if self.closed:
            return
        if self.status == "running":
            self.finish(reason)
            self._publish()
        self.closed = True
        self.checkpoint()
        if self.recorder:
            self.recorder.close()
            self.recorder = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        if exc:
            self.log("errors", {"error": type(exc).__name__, "message": str(exc)})
        self.close("technical_error" if exc else "closed")
