"""Real-time pacing shared by windowed and headless hosts, not by controllers."""
from .controllers import CloudController, RuleController


def make_controller(actor, cloud_config=None):
    if actor == "human":
        return None
    if actor == "rule":
        return RuleController()
    if actor == "cloud" and cloud_config is not None:
        return CloudController(cloud_config)
    raise ValueError("Cloud play requires provider configuration")


class RealtimeRunner:
    def __init__(self, session, controller=None):
        if not session.realtime:
            raise ValueError("RealtimeRunner requires a realtime session")
        self.session, self.controller = session, controller
        self.accumulated = self.active_wall = 0.0
        self.lag_since = None
        self.monitor_at = 0

    def pulse(self, dt, now):
        session = self.session
        if session.status != "running" or session.closed:
            return
        self.accumulated += max(0, dt)
        self.active_wall += max(0, dt)
        if self.controller:
            self.controller.poll(session, now)
        steps = min(10, int((self.accumulated + 1e-9) / 0.020))
        for _ in range(steps):
            session.step_realtime()
            self.accumulated -= 0.020
            if session.status != "running":
                break
        lag_ms = max(0, self.active_wall * 1000 - session.ms)
        if lag_ms > 500:
            self.lag_since = now if self.lag_since is None else self.lag_since
            if now - self.lag_since > 2 and "timing_anomaly" not in session.flags:
                session.flag("timing_anomaly", lag_ms=round(lag_ms))
        else:
            self.lag_since = None
        if session.ms >= self.monitor_at:
            session.log(
                "timing",
                {"active_wall_ms": round(self.active_wall * 1000), "lag_ms": round(lag_ms)},
            )
            self.monitor_at = session.ms + 1000
