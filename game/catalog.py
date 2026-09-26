"""Small, import-safe content registry. Presence here means experiment support, not just assets."""
from dataclasses import dataclass


@dataclass(frozen=True)
class PlantSpec:
    label: str
    constructor: str  # economy / shooter / simple
    parameters: tuple = ("health", "cost", "cooldown_ms")


PLANTS = {
    "SunFlower": PlantSpec("向日葵", "economy"),
    "Peashooter": PlantSpec(
        "豌豆射手",
        "shooter",
        ("health", "cost", "cooldown_ms", "shot_interval_ms", "first_shot_delay_ms"),
    ),
    "WallNut": PlantSpec("坚果", "simple"),
    "SnowPea": PlantSpec(
        "寒冰射手",
        "shooter",
        ("health", "cost", "cooldown_ms", "shot_interval_ms", "first_shot_delay_ms"),
    ),
    "RepeaterPea": PlantSpec(
        "双发射手",
        "shooter",
        ("health", "cost", "cooldown_ms", "shot_interval_ms", "first_shot_delay_ms"),
    ),
    "CherryBomb": PlantSpec("樱桃炸弹", "simple", ("cost", "cooldown_ms")),
    "TallNut": PlantSpec("高坚果", "simple"),
}
ZOMBIES = {
    "Zombie": ("health", "speed"),
    "ConeheadZombie": ("health", "helmet_health", "speed"),
    "BucketheadZombie": ("health", "helmet_health", "speed"),
    "FootballZombie": ("health", "helmet_health", "speed"),
    "FlagZombie": ("health", "speed"),
}
DEFAULT_PLANTS = tuple(PLANTS)[:6]
DEFAULT_ZOMBIES = tuple(ZOMBIES)[:4]


def validate_overrides(overrides, supported, enabled):
    """Only documented numerical knobs; never arbitrary setattr from JSON."""
    if not isinstance(overrides, dict):
        raise ValueError("Content overrides must be an object")
    for name, values in overrides.items():
        if name not in enabled or not isinstance(values, dict):
            raise ValueError("Overrides require an enabled content type")
        allowed = (
            supported[name].parameters
            if isinstance(supported[name], PlantSpec)
            else supported[name]
        )
        for key, value in values.items():
            if key not in allowed:
                raise ValueError(f"Unsupported parameter: {name}.{key}")
            if key == "speed":
                if type(value) not in (int, float) or not 0.05 <= value <= 10:
                    raise ValueError("Zombie speed must be within 0.05..10")
            elif type(value) is not int or not (0 if key == "cost" else 1) <= value <= 1000000:
                raise ValueError(f"Invalid integer parameter: {name}.{key}")
            if key.endswith("_ms") and (value < 20 or value % 20):
                raise ValueError("Timing overrides must be positive multiples of 20ms")


def card_defaults(name):
    from . import constants as c

    info = c.PLANT_CARD_INFO[c.PLANT_CARD_INDEX[name]]
    return info[c.SUN_INDEX], info[c.FROZEN_TIME_INDEX]
