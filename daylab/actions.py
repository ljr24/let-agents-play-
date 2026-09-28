"""Only gateway for controller decisions; validates, queues and commits commands."""
from copy import deepcopy
import json
from .contracts import validate_action
from .placement import placement_reason


class ActionExecutor:
    def __init__(self, session):
        self.session = session

    def _observation_tick(self, observation_id):
        session = self.session
        if not isinstance(observation_id, str):
            return None
        try:
            episode, tick = observation_id.rsplit(":", 1)
            tick = int(tick)
            return tick if episode == session.episode_id and 0 <= tick <= session.tick else None
        except (ValueError, TypeError):
            return None

    def submit(self, action, observation_id, command_id):
        session = self.session
        session._owner()
        action = deepcopy(action)
        try:
            json.dumps(action, allow_nan=False)
        except (ValueError, TypeError):
            action = {"type": "INVALID_INPUT", "error": "NON_JSON_VALUE"}
        obs_tick = self._observation_tick(observation_id)
        reason = None
        if not isinstance(command_id, str) or not command_id or len(command_id) > 200:
            reason = "INVALID_COMMAND_ID"
        elif command_id in session.commands:
            if session.command_payloads[command_id] != action:
                receipt = {
                    "accepted": False,
                    "reason": "COMMAND_ID_CONFLICT",
                    "command_id": command_id,
                }
            else:
                receipt = {**session.commands[command_id], "duplicate": True}
            session.log(
                "submissions",
                dict(
                    action=action, observation_tick=obs_tick, command_id=command_id, receipt=receipt
                ),
            )
            return deepcopy(receipt)
        elif session.closed or session.status != "running":
            reason = "EPISODE_ENDED"
        elif obs_tick is None:
            reason = "INVALID_OBSERVATION"
        elif session.ms - obs_tick * 20 > session.config.max_observation_age_ms:
            reason = "STALE_OBSERVATION"
        elif session.ms - session.last_submit_ms < session.config.action_interval_ms:
            reason = "RATE_LIMITED"
        else:
            reason = validate_action(action)
        receipt = {
            "accepted": reason is None,
            "reason": reason or "QUEUED",
            "command_id": command_id,
        }
        session.log(
            "submissions",
            dict(action=action, observation_tick=obs_tick, command_id=command_id, receipt=receipt),
        )
        if isinstance(command_id, str) and command_id and len(command_id) <= 200:
            session.commands[command_id] = receipt
            session.command_payloads[command_id] = action
        if reason:
            session.emit(
                "action_rejected",
                command_id=command_id,
                action=action,
                reason=reason,
                stage="submission",
            )
        else:
            session.last_submit_ms = session.ms
            context = session.public_context()
            session.log("decisions", {"command_id": command_id, "input": context, "action": action})
            session.queue.append(
                dict(command_id=command_id, action=action, observation_tick=obs_tick,
                     coffee_target=self._coffee_target(action, obs_tick))
            )
        return deepcopy(receipt)

    def _coffee_target(self, action, tick):
        if action.get("plant_type") != "CoffeeBean":
            return None
        obs = self.session.observation_cache.get(tick)
        row, col = action["row"], action["col"]
        if obs and 0 <= row < 5 and 0 <= col < 9:
            return obs["grid"][row][col]
        return None

    def execute(self, item):
        session = self.session
        action = item["action"]
        reason, plant_id = None, None
        if session.ms - item["observation_tick"] * 20 > session.config.max_observation_age_ms:
            reason = "STALE_OBSERVATION"
        elif action["type"] == "PLACE_PLANT":
            name, row, col = action["plant_type"], action["row"], action["col"]
            from .observation import build_observation
            current = build_observation(session)
            reason = placement_reason(current, name, row, col)
            if not reason and name == "CoffeeBean" and (
                    not item.get("coffee_target") or current["grid"][row][col] != item["coffee_target"]):
                reason = "TARGET_CHANGED"
            if not reason:
                obj = session.level.create_plant(name, row, col)
                session.level.commit_plant(obj, row, col)
                plant_id = obj.lab_id
                session.economy.spend(name, session.ms)
                session.emit(
                    "sun_spent", amount=session.prices[name], balance=session.sun, plant_id=plant_id
                )
        elif action["type"] == "REMOVE_PLANT":
            target = session.entities.get(action["plant_id"])
            if target is None or target.lab_kind != "plant" or target.lab_removed or target.name == "CoffeeBean":
                reason = "TARGET_MISSING"
            else:
                plant_id = target.lab_id
                session.level.killPlant(target, shovel=True)
        result = dict(
            command_id=item["command_id"],
            action=action,
            success=reason is None,
            reason=reason or "OK",
            plant_id=plant_id,
        )
        session.emit("action_result", **result)
        session.log("actions", result)
        session.public_actions.append({"sim_ms": session.ms, **result})
