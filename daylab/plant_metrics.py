"""Attribution derived from saved events; never part of model input."""
from collections import Counter, defaultdict


def plant_metrics(events):
    entities = {e["entity_id"]: e for e in events if e["type"].endswith("_created") and "entity_id" in e}
    spending, damage, modifiers, kills = Counter(), Counter(), Counter(), Counter()
    phases = {"前75秒": Counter(), "75秒起": Counter()}
    deployments = defaultdict(list)
    awakening = []
    for e in events:
        if e["type"] == "sun_spent":
            name = entities.get(e["plant_id"], {}).get("entity_type", "unknown")
            spending[name] += e["amount"]
            phases["前75秒" if e["sim_ms"] < 75000 else "75秒起"][name] += e["amount"]
            deployments[name].append(e["sim_ms"])
        elif e["type"] == "plant_awakened":
            awakening.append({k: e[k] for k in ("plant_id", "coffee_id", "sim_ms")})
        elif e["type"] == "damage" and entities.get(e["target_id"], {}).get("type") == "zombie_created" and e["reason"] == "attack":
            actual = sum(max(0, max(0, e["before"].get(k) or 0) - max(0, e["after"].get(k) or 0))
                         for k in ("health", "helmet_health", "helmet_type2_health"))
            origin = e.get("owner_id") or entities.get(e.get("source_id"), {}).get("owner_id") or e.get("source_id")
            name = entities.get(origin, {}).get("entity_type", "unknown")
            bonus = 0
            if e.get("modifier_ids") and e.get("projectile_damage") and e.get("base_damage"):
                bonus = actual * max(0, 1 - e["base_damage"] / e["projectile_damage"])
                modifier = entities.get(e["modifier_ids"][-1], {}).get("entity_type", "unknown")
                modifiers[modifier] += bonus
            damage[name] += actual - bonus
        elif e["type"] == "zombie_death":
            source = entities.get(e.get("source_id"), {})
            origin = entities.get(source.get("owner_id"), source)
            kills[origin.get("entity_type", "unknown")] += 1
    return {
        "各植物支出": dict(spending), "分时支出": {k: dict(v) for k, v in phases.items()},
        "各植物部署毫秒": dict(deployments), "植物基础伤害": dict(damage),
        "火炬附加伤害": dict(modifiers), "击杀归属": dict(kills),
        "咖啡豆支出": spending["CoffeeBean"], "唤醒记录": awakening,
    }
