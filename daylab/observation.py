"""Public observation v1: explicit whitelist, never raw object attributes."""


def build_observation(session):
    plants, zombies, bullets, mowers = [], [], [], []
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
            plants.append(public)
            grid[obj.lab_row][obj.lab_col] = obj.lab_id
        elif obj.lab_kind == "zombie" and obj.lab_id in visible_ids:
            public.update(armored=obj.helmet, slowed=obj.ice_slow_ratio > 1, lost_head=obj.losthead)
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
        plants=plants,
        zombies=zombies,
        bullets=bullets,
        mowers=mowers,
        wave=session.wave,
        rows=5,
        cols=9,
    )
