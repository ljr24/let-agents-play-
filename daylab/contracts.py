"""Public action contract v1. Change validation/schema together and update schema versions."""
from game.catalog import PLANTS as PLANT_CATALOG


def validate_action(action):
    if not isinstance(action, dict):
        return "INVALID_ACTION"
    kind = action.get("type")
    specs = {
        "WAIT": {"type"},
        "PLACE_PLANT": {"type", "plant_type", "row", "col"},
        "REMOVE_PLANT": {"type", "plant_id"},
    }
    if not isinstance(kind, str) or kind not in specs or set(action) != specs[kind]:
        return "INVALID_ACTION"
    if kind == "PLACE_PLANT":
        if not isinstance(action["plant_type"], str):
            return "INVALID_ACTION"
        if type(action["row"]) is not int or type(action["col"]) is not int:
            return "INVALID_COORDINATE"
    if kind == "REMOVE_PLANT" and not isinstance(action["plant_id"], str):
        return "INVALID_TARGET"
    return None


ACTION_SCHEMA = {
    "oneOf": [
        {
            "type": "object",
            "properties": {"type": {"const": "WAIT"}},
            "required": ["type"],
            "additionalProperties": False,
        },
        {
            "type": "object",
            "properties": {
                "type": {"const": "PLACE_PLANT"},
                "plant_type": {"type": "string", "enum": list(PLANT_CATALOG)},
                "row": {"type": "integer", "minimum": 0, "maximum": 4},
                "col": {"type": "integer", "minimum": 0, "maximum": 8},
            },
            "required": ["type", "plant_type", "row", "col"],
            "additionalProperties": False,
        },
        {
            "type": "object",
            "properties": {"type": {"const": "REMOVE_PLANT"}, "plant_id": {"type": "string"}},
            "required": ["type", "plant_id"],
            "additionalProperties": False,
        },
    ]
}
