"""Controllers only receive public observations and submit standard commands."""
from copy import deepcopy
from dataclasses import asdict, dataclass
import json
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

    def __post_init__(self):
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

    @classmethod
    def load(cls, path):
        with open(path, encoding="utf-8-sig") as stream:
            return cls(**json.load(stream))


SYSTEM_PROMPT = (
    "You control a Plants vs Zombies day_lab_v1 experiment. Choose ONE action using only the "
    "provided visible observations and rules. No future or hidden state is available. "
    'Return JSON with exactly one field "action", whose value is one of: '
    '{"type":"WAIT"}, {"type":"PLACE_PLANT","plant_type":"Peashooter","row":0,"col":2}, '
    '{"type":"REMOVE_PLANT","plant_id":"plant-00006"}. '
    "Use only plants in observation.cards. Coordinates are zero based. "
    "Do not add explanations, markdown, extra fields or multiple actions."
)


def make_payload(config, context):
    payload = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": encoded(context)},
        ],
        config.token_limit_field: config.max_output_tokens,
    }
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
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": "pvz_decision", "strict": True, "schema": schema},
        }
    else:
        payload["response_format"] = {"type": "json_object"}
    return payload


def parse_reply(response, context):
    try:
        choice = response["choices"][0]
        if choice["message"].get("refusal"):
            return None, "MODEL_REFUSAL"
        if choice.get("finish_reason") != "stop":
            return None, "INCOMPLETE_RESPONSE"
        value = json.loads(
            choice["message"]["content"],
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
        )
    except (KeyError, IndexError, TypeError, ValueError):
        return None, "INVALID_JSON"
    if not isinstance(value, dict) or set(value) != {"action"}:
        return None, "INVALID_SCHEMA"
    action = value["action"]
    reason = validate_action(action)
    if reason:
        return None, reason
    if action["type"] == "PLACE_PLANT":
        if action["plant_type"] not in {c["plant_type"] for c in context["observation"]["cards"]}:
            return None, "DISABLED_PLANT"
        if not (0 <= action["row"] < 5 and 0 <= action["col"] < 9):
            return None, "OUT_OF_BOUNDS"
    return action, None


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url, code, "Redirect refused", headers, fp)


class ChatCompletions:
    def __init__(self, config):
        self.config = config
        if not os.environ.get(config.api_key_env):
            raise ValueError(f"Missing API key environment variable: {config.api_key_env}")

    def __call__(self, payload):
        key = os.environ[self.config.api_key_env]
        url = self.config.base_url.rstrip("/")
        if not url.endswith("/chat/completions"):
            url += "/chat/completions"
        request = urllib.request.Request(
            url,
            data=encoded(payload).encode(),
            headers={"Content-Type": "application/json", "Authorization": "Bearer " + key},
        )
        with urllib.request.build_opener(NoRedirect()).open(
            request, timeout=self.config.timeout_s
        ) as response:
            raw = response.read(4 * 1024 * 1024 + 1)
            if len(raw) > 4 * 1024 * 1024:
                raise ValueError("Response too large")
        # Defensive redaction even if a misconfigured service echoes authentication.
        return json.loads(raw.decode().replace(key, "[REDACTED]"))


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

    def poll(self, session, now=None):
        now = time.monotonic() if now is None else now
        if self.closed:
            return
        if self.episode_id is None:
            self.episode_id = session.episode_id
            session.log("model_config", asdict(self.config))
        if self.inflight:
            request = self.inflight
            try:
                request_id, response, error, latency = self.results.get_nowait()
            except queue.Empty:
                if now - request["started"] >= self.config.timeout_s and not request["timed_out"]:
                    request["timed_out"] = True
                    self.last_error = "TIMEOUT"
                    session.log(
                        "model_results",
                        {
                            "request_id": request["id"],
                            "error": "TIMEOUT",
                            "latency_ms": (now - request["started"]) * 1000,
                        },
                    )
                return  # don't overlap a timed-out worker with another request
            self.inflight = None
            usage = response.get("usage") if isinstance(response, dict) else None
            total = usage.get("total_tokens") if isinstance(usage, dict) else None
            measured = type(total) is int and total >= 0
            self.used_tokens += total if measured else request["reserved_tokens"]
            action = None
            if request["timed_out"] or latency > self.config.timeout_s * 1000:
                error = "TIMEOUT_LATE_REPLY"
            elif (
                request["episode_id"] != session.episode_id
                or session.status != "running"
                or session.closed
            ):
                error = "EPISODE_CHANGED"
            elif session.ms - request["sim_ms"] > self.config.max_observation_age_ms:
                error = "STALE_REPLY"
            elif error is None:
                action, error = parse_reply(response, request["context"])
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
                ),
            )
            if action is not None and error is None:
                session.submit(
                    action, request["context"]["observation"]["observation_id"], request_id
                )
        if session.closed or session.status != "running" or session.episode_id != self.episode_id:
            return
        if now - self.last_request < self.config.min_interval_s:
            return
        context = session.public_context()
        payload = make_payload(self.config, context)
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
        )
        session.log(
            "model_requests",
            {
                "request_id": request_id,
                "payload": payload,
                "observation_id": context["observation"]["observation_id"],
                "wall_started": time.time(),
            },
        )
        threading.Thread(target=self._work, args=(request_id, payload), daemon=True).start()

    def close(self, session=None):
        self.closed = True
        if self.inflight and session and not session.closed:
            session.log(
                "model_results",
                {
                    "request_id": self.inflight["id"],
                    "error": "CANCELLED_AT_END",
                    "usage": None,
                    "usage_estimated": True,
                    "reserved_tokens": self.inflight["reserved_tokens"],
                },
            )
