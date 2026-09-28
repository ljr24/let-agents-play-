"""Shared public placement rules for humans, cloud preflight and execution."""
SLEEPING_TYPES = frozenset(("FumeShroom", "ScaredyShroom", "DoomShroom"))


def placement_reason(observation, name, row, col):
    cards = {c["plant_type"]: c for c in observation["cards"]}
    if name not in cards:
        return "DISABLED_PLANT"
    if not (0 <= row < observation["rows"] and 0 <= col < observation["cols"]):
        return "OUT_OF_BOUNDS"
    terrain = observation.get("terrain")
    if terrain and terrain[row][col] != "grass":
        return "BLOCKED_TERRAIN"
    target_id = observation["grid"][row][col]
    if name == "CoffeeBean":
        target = next((p for p in observation["plants"] if p["id"] == target_id), None)
        if not target or target["type"] not in SLEEPING_TYPES or not target.get("sleeping"):
            return "NOT_SLEEPING"
        if target.get("waking"):
            return "ALREADY_WAKING"
    elif target_id is not None:
        return "OCCUPIED"
    card = cards[name]
    if observation["sun"] < card["cost"]:
        return "INSUFFICIENT_SUN"
    if card["cooldown_ms"] > 0:
        return "COOLDOWN"
    if not card["ready"]:
        return "CARD_NOT_READY"
    return None
