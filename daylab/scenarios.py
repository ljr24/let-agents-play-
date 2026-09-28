"""Deterministic environment schedules. No game objects and no controller state."""
import random


def make_schedule(config, seed):
    rng = random.Random(seed)
    result = []
    base_rows = list(range(5))
    if config.scenario == "benchmark":
        rng.shuffle(base_rows)
    for wave, count in enumerate(config.wave_counts, 1):
        if config.scenario == "benchmark":
            offset = (wave - 1) % 5
            rows = base_rows[offset:] + base_rows[:offset]
        else:
            rows = list(range(5))
            rng.shuffle(rows)
        names = list(config.wave_types[wave - 1]) if config.wave_types else ["Zombie"] * count
        if not config.wave_types and config.scenario != "economy" and wave >= 4:
            names = ["Zombie" if i % 2 == 0 else "ConeheadZombie" for i in range(count)]
            if wave >= 5:
                names[0] = "BucketheadZombie"
        if not config.wave_types and config.scenario == "rush" and wave >= 4:
            names[-1] = "FootballZombie"
        for i, name in enumerate(names):
            if name not in config.enabled_zombies:
                raise ValueError(f"Scenario requires disabled zombie: {name}")
            result.append(
                dict(
                    at_ms=config.wave_start_ms + (wave - 1) * config.wave_interval_ms,
                    wave=wave,
                    type=name,
                    row=rows[i % 5],
                    x=830,
                )
            )
    return result
