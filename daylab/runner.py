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


def paused_cloud(actor, config):
    return actor == 'cloud' and config is not None and config.decision_mode == 'pause_think'


def make_runner(session, controller):
    if session.execution_mode == 'pause_think':
        return PauseThinkRunner(session, controller)
    return RealtimeRunner(session, controller)


class PauseThinkRunner:
    """Freeze while deciding, then run a bounded simulation interval at display pace."""
    def __init__(self, session, controller):
        if session.realtime or not isinstance(controller, CloudController):
            raise ValueError('PauseThinkRunner requires an offline cloud session')
        self.session, self.controller = session, controller
        if controller.config.advance_after_decision_ms < session.config.action_interval_ms:
            raise ValueError('Decision advance must meet action_interval_ms')
        self.remaining = 0
        self.accumulated = 0.0

    def pulse(self, dt, now):
        s, c = self.session, self.controller
        if s.closed or s.status != 'running':
            return
        if c.paused_reason:
            self.accumulated = 0.0
            return
        if self.remaining:
            self.accumulated += max(0, dt)
            steps = min(10, self.remaining, int((self.accumulated + 1e-9) / .020))
            for _ in range(steps):
                s.advance()
                self.remaining -= 1
                self.accumulated -= .020
                # Update public memory without launching new requests during progression.
                c.poll(s, now, allow_request=False)
                if s.status != 'running':
                    break
            if not self.remaining:
                self.accumulated = 0.0
            return
        # No dt is accumulated during thinking, including the response-arrival pulse.
        had_request = c.inflight is not None
        c.poll(s, now, allow_request=not had_request)
        if s.closed or s.status != 'running':
            return
        if c.paused_reason:
            return
        if had_request and c.inflight is None and not getattr(c, 'pending_repair', None):
            self.remaining = c.config.advance_after_decision_ms // 20
            s.log('decision_timing', {'mode': 'pause_think', 'advance_ms': c.config.advance_after_decision_ms,
                                     'last_error': c.last_error})


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
        if isinstance(self.controller, CloudController) and self.controller.paused_reason:
            self.accumulated = 0.0
            self.active_wall = session.ms / 1000
            self.lag_since = None
            return
        self.accumulated += max(0, dt)
        self.active_wall += max(0, dt)
        if self.controller:
            self.controller.poll(session, now)
            if isinstance(self.controller, CloudController) and self.controller.paused_reason:
                self.accumulated = 0.0
                return
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
