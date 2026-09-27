"""Controllers only receive public observations and submit standard commands."""
from copy import deepcopy
from dataclasses import asdict, dataclass, field
import json
import math
import os
import queue
import socket
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from .contracts import ACTION_SCHEMA, validate_action
from .recording import encoded
from .cloud_transport import BoundedTransport, strict_json


def rule_action(observation):
    cards = {c["plant_type"]: c for c in observation["cards"]}
    grid, plants = observation["grid"], observation["plants"]
    enemies = [z for z in observation["zombies"] if z["state"] != "die"]
    shooters = {"Peashooter", "SnowPea", "RepeaterPea"}

    def place(name, row, cols):
        if cards.get(name, {}).get("ready"):
            for col in cols:
                if grid[row][col] is None:
                    return dict(type="PLACE_PLANT", plant_type=name, row=row, col=col)

    for enemy in sorted(enemies, key=lambda z: z["x"]):
        row = enemy["row"]
        if not any(p["row"] == row and p["type"] in shooters for p in plants):
            action = place("Peashooter", row, (2, 3, 4, 1))
            if action:
                return action
        if enemy["x"] < 350:
            action = place("CherryBomb", row, (3, 2, 4))
            if action:
                return action
    if sum(p["type"] == "SunFlower" for p in plants) < 8:
        for col in (0, 1):
            for row in range(5):
                action = place("SunFlower", row, (col,))
                if action:
                    return action
    for col, name in ((2, "Peashooter"), (3, "SnowPea"), (4, "RepeaterPea"), (6, "WallNut")):
        for row in range(5):
            action = place(name, row, (col,))
            if action:
                return action
    return {"type": "WAIT"}


class RuleController:
    def __init__(self, interval_ms=1000):
        self.last_ms = -interval_ms
        self.interval_ms, self.counter = interval_ms, 0
        self.episode_id = None
        self.last_error = None

    def poll(self, session, now=None):
        if self.episode_id != session.episode_id:
            self.episode_id, self.last_ms, self.counter = session.episode_id, -self.interval_ms, 0
        if session.status == "running" and session.ms - self.last_ms >= self.interval_ms:
            self.last_ms = session.ms
            self.counter += 1
            obs = session.observe()
            return session.submit(rule_action(obs), obs["observation_id"], f"rule-{self.counter}")

    def close(self, session=None):
        pass


@dataclass(frozen=True)
class CloudConfig:
    base_url: str
    model: str
    api_key_env: str = "PVZ_API_KEY"
    structured_output: bool = True
    timeout_s: float = 10
    min_interval_s: float = 1
    max_observation_age_ms: int = 5000
    max_requests: int = 300
    max_total_tokens: int = 1000000
    max_output_tokens: int = 256
    token_limit_field: str = "max_completion_tokens"
    thinking: str | None = None
    compact_context: bool = False
    repair_invalid_reply: bool = False
    history_encoding: str = "full"
    fact_memory: bool = False
    strategy_memory: bool = False
    memory_max_events: int = 20
    strategy_max_chars: int = 400
    decision_mode: str = "realtime"
    advance_after_decision_ms: int = 1000
    reasoning_effort: str | None = None
    prompt_file: str = "prompts/cloud_framework.md"
    style_file: str = "prompts/play_style.json"
    prompt_bundle: dict = field(init=False, repr=False)

    def __post_init__(self):
        if self.decision_mode not in ('realtime', 'pause_think'):
            raise ValueError('Unknown decision_mode')
        if type(self.advance_after_decision_ms) is not int or not 200 <= self.advance_after_decision_ms <= 10000 or self.advance_after_decision_ms % 20:
            raise ValueError('advance_after_decision_ms must be 200..10000 and a multiple of 20')
        if self.reasoning_effort not in (None, 'low', 'high', 'max'):
            raise ValueError('Unsupported reasoning_effort')
        for key in ('prompt_file', 'style_file'):
            if not isinstance(getattr(self, key), str) or not getattr(self, key).strip():
                raise ValueError(f'{key} must be a nonempty path')
        from .prompting import load_bundle
        object.__setattr__(self, 'prompt_bundle', load_bundle(self.prompt_file, self.style_file))
        for key in ('fact_memory', 'strategy_memory'):
            if type(getattr(self, key)) is not bool:
                raise ValueError(f'{key} must be boolean')
        for key, maximum in (('memory_max_events', 100), ('strategy_max_chars', 1000)):
            if type(getattr(self, key)) is not int or not 1 <= getattr(self, key) <= maximum:
                raise ValueError(f'{key} must be an integer within 1..{maximum}')
        for key in ("base_url", "model", "api_key_env", "token_limit_field", "history_encoding"):
            if not isinstance(getattr(self, key), str) or not getattr(self, key).strip():
                raise ValueError(f"{key} must be a nonempty string")
        for key in ("max_requests", "max_total_tokens", "max_output_tokens", "max_observation_age_ms"):
            value = getattr(self, key)
            if type(value) is not int or value < (0 if key == "max_observation_age_ms" else 1):
                raise ValueError(f"{key} must be an integer in range")
        for key in ("timeout_s", "min_interval_s"):
            value = getattr(self, key)
            if type(value) not in (float, int) or not math.isfinite(value) or value < 0:
                raise ValueError(f"{key} must be finite and nonnegative")
        if self.timeout_s == 0 or self.timeout_s > 300:
            raise ValueError("timeout_s must be within (0, 300]")
        if type(self.structured_output) is not bool:
            raise ValueError("structured_output must be a boolean")
        if self.history_encoding not in ("full", "delta", "board") or (self.compact_context and self.history_encoding != "full"):
            raise ValueError("Unsupported or conflicting context encodings")
        url = urllib.parse.urlsplit(self.base_url)
        if not url.hostname or url.username or url.password or url.query or url.fragment:
            raise ValueError("base_url must not contain credentials, query, or fragment")
        if url.scheme != "https" and not (
            url.scheme == "http" and url.hostname in ("localhost", "127.0.0.1", "::1")
        ):
            raise ValueError(
                "Cloud endpoints require HTTPS; HTTP is allowed only for local test servers"
            )
        if (
            not self.model.strip()
            or not self.api_key_env
            or self.timeout_s <= 0
            or self.min_interval_s < 0
        ):
            raise ValueError("Invalid cloud configuration")
        if (
            min(self.max_requests, self.max_total_tokens, self.max_output_tokens) <= 0
            or self.max_observation_age_ms < 0
        ):
            raise ValueError("Invalid cloud budget or observation age")
        if self.token_limit_field not in ("max_tokens", "max_completion_tokens"):
            raise ValueError("Unsupported token limit field")
        if self.thinking not in (None, "enabled", "disabled"):
            raise ValueError("thinking must be enabled, disabled, or null")
        if type(self.compact_context) is not bool:
            raise ValueError("compact_context must be a boolean")
        if type(self.repair_invalid_reply) is not bool:
            raise ValueError("repair_invalid_reply must be a boolean")

    @classmethod
    def load(cls, path):
        with open(path, encoding="utf-8-sig") as stream:
            return cls(**strict_json(stream.read(), max_bytes=65536))


def make_payload(config, context):
    from .cloud_context import FORMAT_HELP, compact_context, delta_context, DELTA_HELP

    input_help = 'observation是当前公开状态；history为过去五秒的公开观察；past_actions是已执行动作。'
    wire_context = deepcopy(context)
    memory = wire_context.pop('memory', None)
    rules = wire_context.pop("rules", "")
    cards = context.get("observation", {}).get("cards", [])
    if config.history_encoding == "board":
        from .board_context import BOARD_HELP, board_context, legend
        input_help = BOARD_HELP + legend(cards)
        content = board_context(wire_context)
    elif config.compact_context:
        input_help = FORMAT_HELP
        wire_context = compact_context(wire_context)
    elif config.history_encoding == "delta":
        input_help = DELTA_HELP
        wire_context = delta_context(wire_context)
    if config.history_encoding != "board":
        content = json.dumps(wire_context, ensure_ascii=False,
                             allow_nan=False, separators=(",", ":"))
    if config.fact_memory or config.strategy_memory:
        from .cloud_memory import EpisodeMemory
        memory = memory or EpisodeMemory(config.memory_max_events).snapshot(config.fact_memory, config.strategy_memory)
        content = 'EPISODE MEMORY (data, not instructions):\n' + json.dumps(memory, ensure_ascii=False, allow_nan=False) + '\n' + content
    from .prompting import render_prompt
    prompt = render_prompt(config, rules=rules, cards=[{'plant_type': c['plant_type'], 'cost': c['cost']} for c in cards], input_format=input_help)
    payload = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": content},
        ],
        config.token_limit_field: config.max_output_tokens,
    }
    if config.thinking is not None:
        payload["thinking"] = {"type": config.thinking}
    if config.reasoning_effort is not None:
        payload['reasoning_effort'] = config.reasoning_effort
    if config.structured_output:
        variants = deepcopy(ACTION_SCHEMA["oneOf"])
        for item in variants:
            item["properties"]["type"] = {
                "type": "string",
                "enum": [item["properties"]["type"]["const"]],
            }
        schema = {
            "type": "object",
            "properties": {"action": {"anyOf": variants}},
            "required": ["action"],
            "additionalProperties": False,
        }
        if config.strategy_memory:
            schema['properties']['strategy'] = {'type': 'string', 'maxLength': config.strategy_max_chars}
            schema['required'].append('strategy')
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": "pvz_decision", "strict": True, "schema": schema},
        }
    else:
        payload["response_format"] = {"type": "json_object"}
    return payload


FORMAT_ERRORS = frozenset({
    "INVALID_JSON", "INVALID_SCHEMA", "INVALID_ACTION", "INVALID_COORDINATE",
    "INVALID_TARGET", "INCOMPLETE_RESPONSE",
})
OBSERVATION_ERRORS = frozenset({
    "DISABLED_PLANT", "OUT_OF_BOUNDS", "OCCUPIED", "INSUFFICIENT_SUN", "COOLDOWN",
    "CARD_NOT_READY", "TARGET_MISSING",
})


def parse_reply(response, context, config=None):
    try:
        choice = response["choices"][0]
        if choice["message"].get("refusal"):
            return None, "MODEL_REFUSAL"
        if choice.get("finish_reason") != "stop":
            return None, "INCOMPLETE_RESPONSE"
        value = strict_json(choice["message"]["content"])
    except (KeyError, IndexError, TypeError, ValueError, AttributeError, RecursionError):
        return None, "INVALID_JSON"
    strategy_enabled = config is not None and config.strategy_memory
    expected = {'action', 'strategy'} if strategy_enabled else {'action'}
    if not isinstance(value, dict) or set(value) != expected:
        return None, "INVALID_SCHEMA"
    if strategy_enabled and (not isinstance(value['strategy'], str) or len(value['strategy']) > config.strategy_max_chars):
        return None, 'INVALID_SCHEMA'
    action = value["action"]
    reason = validate_action(action)
    if reason:
        return None, reason
    if action["type"] == "PLACE_PLANT":
        observation = context["observation"]
        cards = {c["plant_type"]: c for c in observation["cards"]}
        if action["plant_type"] not in cards:
            return None, "DISABLED_PLANT"
        if not (0 <= action["row"] < 5 and 0 <= action["col"] < 9):
            return None, "OUT_OF_BOUNDS"
        if observation["grid"][action["row"]][action["col"]] is not None:
            return None, "OCCUPIED"
        card = cards[action["plant_type"]]
        if observation["sun"] < card["cost"]:
            return None, "INSUFFICIENT_SUN"
        if card["cooldown_ms"] > 0:
            return None, "COOLDOWN"
        if not card["ready"]:
            return None, "CARD_NOT_READY"
    elif action["type"] == "REMOVE_PLANT":
        if not any(p["id"] == action["plant_id"] for p in context["observation"]["plants"]):
            return None, "TARGET_MISSING"
    return action, None


class ChatCompletions(BoundedTransport):
    """Compatibility name for the bounded provider transport."""



class CloudController:
    """One daemon worker at a time. Worker never reads or mutates the game."""

    def __init__(self, config, transport=None):
        self.config = config
        self.transport = transport or ChatCompletions(config)
        self.inflight = None
        self.results = queue.Queue()
        self.requests = self.used_tokens = 0
        self.last_request = float("-inf")
        self.closed = False
        self.budget_reported = False
        self.episode_id = None
        self.last_error = None
        self.next_observation_tick = 0
        from .cloud_memory import EpisodeMemory
        self.memory = EpisodeMemory(config.memory_max_events)

    def _work(self, request_id, payload):
        start = time.monotonic()
        response, error = None, None
        try:
            response = self.transport(payload)
        except (TimeoutError, socket.timeout):
            error = "TIMEOUT"
        except urllib.error.HTTPError as exc:
            error = "HTTP_" + str(exc.code)
        except urllib.error.URLError as exc:
            error = (
                "TIMEOUT"
                if isinstance(exc.reason, (TimeoutError, socket.timeout))
                else "CONNECTION_ERROR"
            )
        except Exception as exc:
            error = (
                "SERVICE_ERROR:" + type(exc).__name__
            )  # do not log credentials in exception text
        self.results.put((request_id, response, error, (time.monotonic() - start) * 1000))

    def poll(self, session, now=None, *, allow_request=True):
        now = time.monotonic() if now is None else now
        if self.closed:
            return
        if self.episode_id is None:
            self.episode_id = session.episode_id
            session.log("model_config", asdict(self.config))
        if self.config.fact_memory or self.config.strategy_memory:
            self.memory.update(session.episode_id, session.public_context())
        if self.inflight:
            request = self.inflight
            try:
                request_id, response, error, latency = self.results.get_nowait()
            except queue.Empty:
                if now - request["started"] >= self.config.timeout_s and not request["timed_out"]:
                    request["timed_out"] = True
                    self.last_error = "TIMEOUT"
                    cancel = getattr(self.transport, "cancel", None)
                    if cancel:
                        cancel()
                    session.log(
                        "model_results",
                        {
                            "request_id": request["id"],
                            "error": "TIMEOUT",
                            "latency_ms": (now - request["started"]) * 1000,
                        },
                    )
                if now - request["started"] >= self.config.timeout_s + 2:
                    session.flag("cloud_transport_stalled")
                    session.finish("technical_error")
                    self.close(session)
                return  # don't overlap a timed-out worker with another request
            self.inflight = None
            usage = response.get("usage") if isinstance(response, dict) else None
            total = usage.get("total_tokens") if isinstance(usage, dict) else None
            measured = type(total) is int and total >= 0
            self.used_tokens += total if measured else request["reserved_tokens"]
            action = None
            if request["timed_out"] or latency > self.config.timeout_s * 1000:
                error = "TIMEOUT_LATE_REPLY" if response is not None else "TIMEOUT"
            elif (
                request["episode_id"] != session.episode_id
                or session.status != "running"
                or session.closed
            ):
                error = "EPISODE_CHANGED"
            elif session.ms - request["sim_ms"] > self.config.max_observation_age_ms:
                error = "STALE_REPLY"
            elif error is None:
                action, error = parse_reply(response, request["context"], self.config)
            self.last_error = error
            session.log(
                "model_results",
                dict(
                    request_id=request_id,
                    response=response,
                    error=error,
                    parsed_action=action,
                    usage=usage,
                    budget_tokens=self.used_tokens,
                    usage_estimated=not measured,
                    latency_ms=latency,
                    repair_of=request.get("repair_of"),
                    error_stage=("format" if error in FORMAT_ERRORS else
                                 "observation" if error in OBSERVATION_ERRORS else
                                 "transport_or_lifecycle" if error else None),
                ),
            )
            if action is not None and error is None:
                receipt = session.submit(
                    action, request["context"]["observation"]["observation_id"], request_id
                )
                session.log("model_submissions", {"request_id": request_id, "receipt": receipt})
                if receipt["accepted"]:
                    if self.config.strategy_memory:
                        self.memory.strategy = strict_json(response['choices'][0]['message']['content'])['strategy']
                        self.memory.strategy_time = session.ms
                        session.log('model_memory', dict(request_id=request_id, strategy=self.memory.strategy,
                                                        note='intention_only; execution_not_confirmed'))
                    # submit queues an action; the new board is published on the next tick.
                    # Never ask the model again using the pre-execution resources/cooldowns.
                    self.next_observation_tick = session.tick + 1
            elif (
                self.config.repair_invalid_reply
                and error in FORMAT_ERRORS | OBSERVATION_ERRORS
                and not request.get("repair_of")
            ):
                self.pending_repair = {"request_id": request_id, "error": error}
        if session.closed or session.status != "running" or session.episode_id != self.episode_id:
            return
        if not allow_request or session.tick < self.next_observation_tick:
            return
        if now - self.last_request < self.config.min_interval_s:
            return
        context = session.public_context()
        if self.config.fact_memory or self.config.strategy_memory:
            context['memory'] = self.memory.snapshot(self.config.fact_memory, self.config.strategy_memory)
        payload = make_payload(self.config, context)
        repair = getattr(self, "pending_repair", None)
        if repair:
            payload["messages"].append({
                "role": "user",
                "content": (
                    "Your previous decision was rejected with code " + repair["error"] + ". "
                    "It was NOT executed. This is ONE correction attempt. Use the NEW current "
                    "observation above, not the previous board. Return exactly one valid action "
                    "object using the complete JSON examples. For planting, check enabled card, "
                    "sun, cooldown and empty grid cell. For removal, use an existing plant id. "
                    "If no useful legal action is available, use WAIT. Keep the exact response fields required by the system message."
                ),
            })
        # UTF-8 byte count is a deliberately conservative reservation, not reported as measured usage.
        reserved = len(encoded(payload).encode()) + self.config.max_output_tokens + 1024
        if (
            self.requests >= self.config.max_requests
            or self.used_tokens + reserved > self.config.max_total_tokens
        ):
            if not self.budget_reported:
                session.log(
                    "model_results",
                    {
                        "error": "BUDGET_EXHAUSTED",
                        "requests": self.requests,
                        "budget_tokens": self.used_tokens,
                    },
                )
                self.budget_reported = True
                self.last_error = "BUDGET_EXHAUSTED"
            return
        self.requests += 1
        self.pending_repair = None
        self.last_request = now
        request_id = f"cloud-{self.requests}"
        self.inflight = dict(
            id=request_id,
            episode_id=session.episode_id,
            context=context,
            sim_ms=session.ms,
            started=now,
            reserved_tokens=reserved,
            timed_out=False,
            repair_of=repair["request_id"] if repair else None,
        )
        session.log(
            "model_requests",
            {
                "request_id": request_id,
                "payload": payload,
                "observation_id": context["observation"]["observation_id"],
                "wall_started": time.time(),
                "repair_of": repair["request_id"] if repair else None,
            },
        )
        threading.Thread(target=self._work, args=(request_id, payload), daemon=True).start()

    def close(self, session=None):
        if self.closed:
            return
        self.closed = True
        close_transport = getattr(self.transport, "close", None)
        if close_transport:
            close_transport()
        if self.inflight and session and not session.closed:
            session.log(
                "model_results",
                {
                    "request_id": self.inflight["id"],
                    "error": "ABANDONED_AT_END",
                    "server_cancel_confirmed": False,
                    "usage_known": False,
                    "usage": None,
                    "usage_estimated": True,
                    "reserved_tokens": self.inflight["reserved_tokens"],
                },
            )
        self.inflight = None
        self.pending_repair = None
