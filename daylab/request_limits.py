"""Bound request context without clipping the current board or corrupting JSON."""
from copy import deepcopy
from .recording import encoded


class InputLimitError(ValueError):
    def __init__(self, diagnostics):
        super().__init__("INPUT_TOO_LARGE")
        self.diagnostics = diagnostics


def prepare_request(config, context, payload_builder, *, output_tokens=None, repair=None):
    data = deepcopy(context)
    output_tokens = output_tokens or config.max_output_tokens
    removed_frames = removed_facts = 0
    while True:
        payload = payload_builder(config, data)
        payload[config.token_limit_field] = output_tokens
        if repair:
            payload["messages"].append({"role": "user", "content":
                "Previous attempt failed: " + repair["error"] + ". It was not executed. "
                "This is the only retry. Decide from CURRENT, using exactly the required JSON fields. "
                "CoffeeBean targets an existing sleeping, non-waking mushroom; other plants need empty grass."})
        # Explicit fallback: conservative UTF-8 size estimate, never reported as actual usage.
        input_bytes = len(encoded({k: v for k, v in payload.items()
                                   if k not in ("model", config.token_limit_field)}).encode("utf-8"))
        estimate = input_bytes + 1024
        cap = config.max_input_tokens
        if config.context_window_tokens:
            cap = min(cap, config.context_window_tokens - output_tokens)
        obs = data["observation"]
        diagnostics = dict(
            input_bytes=input_bytes, estimated_input_tokens=estimate,
            estimator="utf8_bytes_plus_1024_conservative", max_input_tokens=config.max_input_tokens,
            context_window_tokens=config.context_window_tokens, output_limit=output_tokens,
            history_frames=len(data.get("history", [])),
            memory_facts=len(data.get("memory", {}).get("facts", [])),
            removed_history_frames=removed_frames, removed_memory_facts=removed_facts,
            section_bytes={key: len(encoded(data.get(key)).encode("utf-8"))
                           for key in ("rules", "observation", "history", "past_actions", "memory")},
            entity_counts={key: len(obs.get(key, [])) for key in ("plants", "zombies", "bullets", "overlays")},
        )
        if estimate <= cap:
            return payload, data, diagnostics
        if data.get("history"):
            data["history"].pop(0)
            removed_frames += 1
        elif data.get("memory", {}).get("facts"):
            data["memory"]["facts"].pop(0)
            removed_facts += 1
        else:
            raise InputLimitError(diagnostics)
