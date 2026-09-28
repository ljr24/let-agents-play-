from dataclasses import dataclass, fields, field
import json
from types import MappingProxyType
from game.catalog import (
    PLANTS as PLANT_CATALOG,
    ZOMBIES as ZOMBIE_CATALOG,
    DEFAULT_PLANTS,
    DEFAULT_ZOMBIES,
    validate_overrides,
)

PLANTS = DEFAULT_PLANTS
ZOMBIES = DEFAULT_ZOMBIES
SCENARIOS = ("economy", "armor", "rush", "benchmark")
LABELS = {"economy": "经济建设", "armor": "装甲压力", "rush": "快速突袭", "benchmark": "十档关卡"}
NAMES = {name: spec.label for name, spec in PLANT_CATALOG.items()}
RULES = (
    "白天5行9列。阳光自动入账，每7秒自然产出25。向日葵种下6秒首次产25，"
    "此后每24秒产25。每行一辆小推车。可以种植、铲除、等待；铲除不退款。"
    "行列从0开始。每200毫秒最多提交一次决策。"
    "豌豆射手攻击本行；寒冰射手使目标减速；双发射手连发两颗；"
    "坚果用于阻挡；樱桃炸弹短暂准备后造成周围三行范围伤害并消耗。"
    "路障、铁桶和橄榄球有防具，橄榄球移动较快。"
)


@dataclass(frozen=True)
class ExperimentConfig:
    profile: str = "day_lab_v1"
    scenario: str = "economy"
    enabled_plants: tuple = PLANTS
    enabled_zombies: tuple = ZOMBIES
    initial_sun: int = 150
    max_time_ms: int = 300000
    tick_ms: int = 20
    action_interval_ms: int = 200
    max_observation_age_ms: int = 5000
    actor: str = "human"
    practice: bool = False
    plant_overrides: dict = field(default_factory=dict)
    zombie_overrides: dict = field(default_factory=dict)
    wave_interval_ms: int = 25000
    wave_start_ms: int = 18000
    wave_counts: tuple = (1, 2, 3, 4, 5, 6)
    wave_types: tuple = ()
    level_id: str = ""
    scheme_id: str = ""
    benchmark_version: str = ""

    def __post_init__(self):
        if self.level_id and self.level_id not in tuple(f"{i:02d}" for i in range(1, 11)):
            raise ValueError("level_id must be 01..10")
        if self.scheme_id and self.scheme_id not in ("A", "B", "C"):
            raise ValueError("scheme_id must be A/B/C")
        if self.scenario == "benchmark" and not (self.level_id and self.scheme_id and self.benchmark_version and self.wave_types):
            raise ValueError("Use load_benchmark() to create benchmark conditions")
        for key in (
            "initial_sun",
            "max_time_ms",
            "tick_ms",
            "action_interval_ms",
            "max_observation_age_ms",
            "wave_interval_ms",
            "wave_start_ms",
        ):
            if type(getattr(self, key)) is not int:
                raise ValueError(f"{key} must be an integer")
        object.__setattr__(self, "enabled_plants", tuple(self.enabled_plants))
        object.__setattr__(self, "enabled_zombies", tuple(self.enabled_zombies))
        if self.profile != "day_lab_v1" or self.scenario not in SCENARIOS:
            raise ValueError("Unsupported experiment profile or scenario")
        if self.tick_ms != 20 or self.action_interval_ms < 20:
            raise ValueError("day_lab_v1 requires 20ms ticks and a positive action interval")
        if not 0 <= self.initial_sun <= 9990 or self.max_time_ms <= 0 or self.max_time_ms % 20:
            raise ValueError("Invalid resource or time limit")
        if self.max_observation_age_ms < 0:
            raise ValueError("Invalid observation age")
        for selected, supported in (
            (self.enabled_plants, PLANT_CATALOG),
            (self.enabled_zombies, ZOMBIE_CATALOG),
        ):
            if (
                not selected
                or len(set(selected)) != len(selected)
                or not set(selected) <= set(supported)
            ):
                raise ValueError("Only validated day_lab_v1 content can be enabled")
        if self.actor not in ("human", "rule", "cloud", "test"):
            raise ValueError("Unknown controller")
        object.__setattr__(self, "wave_counts", tuple(self.wave_counts))
        object.__setattr__(self, "wave_types", tuple(tuple(wave) for wave in self.wave_types))
        if (
            not self.wave_counts
            or len(self.wave_counts) > 100
            or any(type(n) is not int or not 1 <= n <= 100 for n in self.wave_counts)
            or self.wave_start_ms < 0
            or self.wave_interval_ms < 20
            or self.wave_start_ms % 20
            or self.wave_interval_ms % 20
        ):
            raise ValueError("Invalid wave timing/counts")
        if self.wave_types and (
            len(self.wave_types) != len(self.wave_counts)
            or any(
                len(wave) != count or any(name not in self.enabled_zombies for name in wave)
                for wave, count in zip(self.wave_types, self.wave_counts)
            )
        ):
            raise ValueError("wave_types must match wave_counts and enabled zombies")
        for key, catalog, enabled in (
            ("plant_overrides", PLANT_CATALOG, self.enabled_plants),
            ("zombie_overrides", ZOMBIE_CATALOG, self.enabled_zombies),
        ):
            raw = getattr(self, key)
            value = (
                {name: dict(params) for name, params in raw.items()}
                if isinstance(raw, MappingProxyType)
                else raw
            )
            validate_overrides(value, catalog, enabled)
            object.__setattr__(
                self,
                key,
                MappingProxyType(
                    {name: MappingProxyType(dict(params)) for name, params in value.items()}
                ),
            )

    def to_dict(self):
        data = {f.name: getattr(self, f.name) for f in fields(self)}
        for key in ("plant_overrides", "zombie_overrides"):
            data[key] = {name: dict(params) for name, params in data[key].items()}
        # Omit V2 defaults so unmodified day_lab_v1 conditions keep their identity.
        defaults = {
            "plant_overrides": {},
            "zombie_overrides": {},
            "wave_interval_ms": 25000,
            "wave_start_ms": 18000,
            "wave_counts": (1, 2, 3, 4, 5, 6),
            "wave_types": (),
            "level_id": "",
            "scheme_id": "",
            "benchmark_version": "",
        }
        for key, value in defaults.items():
            if data[key] == value:
                data.pop(key)
        return data

    @classmethod
    def from_dict(cls, value):
        data = dict(value)
        if set(data) - {f.name for f in fields(cls)}:
            raise ValueError("Unknown configuration fields")
        for key in ("enabled_plants", "enabled_zombies"):
            if key in data:
                data[key] = tuple(data[key])
        return cls(**data)


def rules_text(config):
    """Public static rules only; never reveal the generated future schedule."""
    value = RULES.replace("每200毫秒", f"每{config.action_interval_ms}毫秒")
    value += (f" 本局共{len(config.wave_counts)}波，时限{config.max_time_ms / 1000:g}秒。"
              "守住家园并消灭全部波次敌人才是胜利；最后一波开始不等于胜利。"
              "达到时限记为超时，不是胜利。")
    if "TallNut" in config.enabled_plants:
        value += "高坚果是更耐久的阻挡植物。"
    if "FlagZombie" in config.enabled_zombies:
        value += "旗帜僵尸比普通僵尸移动稍快。"
    details = {
        "Threepeater": "三线射手攻击本行及上下相邻行，边缘行只攻击存在的行。",
        "StarFruit": "杨桃向后、上下和右上右下斜向攻击，不向正右方直射。",
        "TorchWood": "火炬树桩不主动攻击，把经过的普通豌豆变成火焰弹；寒冰弹先变回普通豌豆并失去减速。",
        "PotatoMine": "土豆地雷种下后需要约15秒准备，准备好后接触敌人爆炸并消耗。",
        "Spikeweed": "地刺对经过其位置的敌人持续造成伤害，不能阻挡敌人。",
        "Squash": "窝瓜在附近有敌人时扑击，使用一次后消耗。",
        "Jalapeno": "火爆辣椒短暂准备后对本行造成范围伤害并消耗。",
        "FumeShroom": "大喷菇短程范围攻击本行多个敌人，攻击可穿过铁门护盾。",
        "ScaredyShroom": "胆小菇远程攻击本行，但敌人接近时退缩停火。",
        "DoomShroom": "毁灭菇唤醒后短暂准备，造成大范围伤害并留下不能种植的弹坑。",
        "CoffeeBean": "白天大喷菇、胆小菇、毁灭菇默认休眠，必须在休眠蘑菇所在格种咖啡豆，唤醒动画完成才生效。咖啡豆75阳光，另占一次操作及独立卡片冷却；不能种在空地、已清醒或正在唤醒的蘑菇上。",
    }
    value += "".join(details.get(name, "") for name in config.enabled_plants)
    value += "撑杆僵尸可跳过普通坚果，高坚果阻止其跳跃；铁门提供盾牌防护；读报破纸后加速。" if any(n in config.enabled_zombies for n in ("PoleVaultingZombie", "ScreenDoorZombie", "NewspaperZombie")) else ""
    parameters = {
        key: config.to_dict().get(key)
        for key in ("plant_overrides", "zombie_overrides")
        if config.to_dict().get(key)
    }
    if parameters:
        value += "本实验的静态参数覆盖：" + json.dumps(parameters, ensure_ascii=False, sort_keys=True)
    return value


# Compatibility exports for existing local scripts. New code imports their owning modules.
from .scenarios import make_schedule
from .contracts import validate_action, ACTION_SCHEMA

__all__ = [
    "ExperimentConfig",
    "PLANTS",
    "ZOMBIES",
    "SCENARIOS",
    "LABELS",
    "NAMES",
    "RULES",
    "rules_text",
    "make_schedule",
    "validate_action",
    "ACTION_SCHEMA",
]
