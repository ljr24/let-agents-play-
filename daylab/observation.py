"""Public observation v3: explicit whitelist, never raw object attributes."""


def build_observation(session):
    from game import constants as c
    plants, zombies, bullets, mowers, overlays = [], [], [], [], []
    coffees = {p.target_id for group in session.level.plant_groups for p in group if p.name == "CoffeeBean"}
    terrain = [["crater" if c.HOLE in cell[c.MAP_PLANT] else "grass" for cell in row]
               for row in session.level.map.map]
    visible_ids = session.level.visible_entity_ids()
    grid = [[None] * 9 for _ in range(5)]
    for obj in session.entities.values():
        if obj.lab_removed:
            continue
        public = dict(
            id=obj.lab_id,
            type=getattr(obj, "name", obj.lab_kind),
            row=obj.lab_row,
            x=obj.rect.x,
            y=obj.rect.y,
            state=obj.state,
        )
        if obj.lab_kind == "plant":
            public.update(
                col=obj.lab_col,
                appearance=(
                    "cracked2"
                    if getattr(obj, "cracked2", False)
                    else "cracked1"
                    if getattr(obj, "cracked1", False)
                    else "normal"
                ),
            )
            if obj.name == "CoffeeBean":
                public["target_id"] = obj.target_id
                overlays.append(public)
                continue
            public["sleeping"] = obj.state == c.SLEEP
            public["waking"] = obj.lab_id in coffees
            if obj.name == "PotatoMine":
                public["armed"] = not obj.is_init
            plants.append(public)
            grid[obj.lab_row][obj.lab_col] = obj.lab_id
        elif obj.lab_kind == "zombie" and obj.lab_id in visible_ids:
            public.update(armored=bool(obj.helmet or obj.helmet_type2),
                          shield=bool(obj.helmet_type2), slowed=obj.ice_slow_ratio > 1,
                          lost_head=obj.losthead, jumping=getattr(obj, "jumping", False),
                          jumped=getattr(obj, "jumped", False),
                          paper_broken=obj.name == "NewspaperZombie" and not obj.helmet_type2)
            zombies.append(public)
        elif obj.lab_kind == "bullet" and obj.lab_id in visible_ids:
            bullets.append(public)
        elif obj.lab_kind == "mower":
            if obj.lab_id not in visible_ids:
                public.update(x=None, y=None)
            mowers.append(public)
    cards = []
    for name in session.config.enabled_plants:
        remaining = max(0, session.cooldowns[name] - session.ms)
        cards.append(
            dict(
                plant_type=name,
                cost=session.prices[name],
                cooldown_ms=remaining,
                ready=remaining == 0 and session.sun >= session.prices[name],
                cooldown_progress=1 - remaining / session.cooldown_lengths[name],
            )
        )
    return dict(
        observation_id=f"{session.episode_id}:{session.tick}",
        tick=session.tick,
        sim_ms=session.ms,
        status=session.status,
        sun=session.sun,
        cards=cards,
        grid=grid,
        terrain=terrain,
        overlays=overlays,
        plants=plants,
        zombies=zombies,
        bullets=bullets,
        mowers=mowers,
        wave=session.wave,
        total_waves=len(session.config.wave_counts),
        time_limit_ms=session.config.max_time_ms,
        remaining_time_ms=max(0, session.config.max_time_ms - session.ms),
        rows=5,
        cols=9,
    )
