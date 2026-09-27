"""Lossless request-only encoding. Public observations and stored game data stay unchanged."""
from copy import deepcopy


DELTA_HELP = (
    '\nHistory encoding: history_reverse_deltas_v1. observation is the full CURRENT state. '
    'history is a list of patch lists, newest past snapshot first. Starting from a COPY of '
    'observation, apply each patch list in sequence to recover each older snapshot. '
    'A patch ["set",path,value] replaces the field at path; ["del",path] removes it. '
    'Path elements are object keys or zero-based array indices; [] means the root. '
    'Never treat historical occupancy or cooldown as current. No historical information is omitted. '
)


def delta_context(context):
    result = deepcopy(context)
    previous = result["observation"]
    deltas = []
    for snapshot in reversed(result.get("history", [])):
        deltas.append(_delta(previous, snapshot))
        previous = snapshot
    result["history"] = deltas
    result["history_encoding"] = "history_reverse_deltas_v1"
    return result


def expand_delta_context(context):
    result = deepcopy(context)
    if result.pop("history_encoding") != "history_reverse_deltas_v1":
        raise ValueError("Unsupported history encoding")
    state = deepcopy(result["observation"])
    history = []
    for patches in result["history"]:
        for patch in patches:
            op, path = patch[:2]
            if not path:
                state = deepcopy(patch[2])
                continue
            parent = state
            for key in path[:-1]:
                parent = parent[key]
            if op == "del":
                del parent[path[-1]]
            else:
                parent[path[-1]] = deepcopy(patch[2])
        history.append(deepcopy(state))
    result["history"] = list(reversed(history))
    return result


FORMAT_HELP = (
    'Input uses compact_public_v1, a lossless encoding of public information. '
    'Any {"$table":{"columns":[...],"rows":[...]}} represents a list of objects: '
    'zip columns with each row to recover their fields. Expand tables recursively first. '
    'observation is the CURRENT state. history.base is the oldest past observation; '
    'apply each history.deltas list in order to the preceding history state to recover '
    'the next past observation. Each patch is [op,path,value] for set or [op,path] for del; '
    'path elements are object keys or zero-based list indices; empty path replaces the root. '
    'History is past information, never the current board. past_actions are already completed. '
)


def _pack(value):
    if isinstance(value, dict):
        return {key: _pack(item) for key, item in value.items()}
    if isinstance(value, list):
        if value and all(isinstance(item, dict) for item in value):
            columns = sorted(value[0])
            if all(sorted(item) == columns for item in value):
                return {"$table": {"columns": columns, "rows": [
                    [_pack(item[key]) for key in columns] for item in value
                ]}}
        return [_pack(item) for item in value]
    return value


def _unpack(value):
    if isinstance(value, dict):
        if set(value) == {"$table"}:
            table = value["$table"]
            return [dict(zip(table["columns"], [_unpack(v) for v in row]))
                    for row in table["rows"]]
        return {key: _unpack(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_unpack(item) for item in value]
    return value


def _delta(before, after, path=()):
    if type(before) is type(after) and before == after:
        return []
    if isinstance(before, dict) and isinstance(after, dict):
        changes = [["del", [*path, key]] for key in sorted(before.keys() - after.keys())]
        for key in sorted(after):
            changes.extend(_delta(before[key], after[key], (*path, key)) if key in before
                           else [["set", [*path, key], deepcopy(after[key])]])
        return changes
    if isinstance(before, list) and isinstance(after, list) and len(before) == len(after):
        return [change for i, (a, b) in enumerate(zip(before, after))
                for change in _delta(a, b, (*path, i))]
    return [["set", list(path), deepcopy(after)]]


def compact_context(context):
    """Keep every field, including all five seconds of public history; no hidden inputs."""
    result = deepcopy(context)
    history = result.pop("history", [])
    result["history"] = {
        "base": history[0] if history else None,
        "deltas": [_delta(a, b) for a, b in zip(history, history[1:])],
    }
    return {"format": "compact_public_v1", "context": _pack(result)}


def expand_context(value):
    """Reference decoder for audits, offline comparisons and compatibility checks."""
    if value.get("format") != "compact_public_v1":
        raise ValueError("Unknown cloud context format")
    result = _unpack(value["context"])
    encoded_history = result["history"]
    history = [] if encoded_history["base"] is None else [encoded_history["base"]]
    for changes in encoded_history["deltas"]:
        state = deepcopy(history[-1])
        for change in changes:
            op, path = change[:2]
            if not path:
                state = deepcopy(change[2])
                continue
            parent = state
            for key in path[:-1]:
                parent = parent[key]
            if op == "del":
                del parent[path[-1]]
            else:
                parent[path[-1]] = deepcopy(change[2])
        history.append(state)
    result["history"] = history
    return result
