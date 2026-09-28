"""Internal checkpoint encoding v1. Never pass this data to decision controllers."""
import math
import pygame as pg
from .recording import clean


def entity_state(entity):
    """All scalar logic/timers plus explicit frame/mask identities; never pickle sprites."""
    state = {}
    for key, value in sorted(vars(entity).items()):
        if key.startswith(("_", "lab")) or key in ("image", "mask", "frames"):
            continue
        if value is None or isinstance(value, (str, int, float, bool)):
            state[key] = value
        elif isinstance(value, pg.Rect):
            state[key] = list(value)
        elif hasattr(value, "lab_id"):
            state[key] = value.lab_id
    frame_names = [
        k
        for k, v in vars(entity).items()
        if k != "frames" and k.endswith("frames") and v is getattr(entity, "frames", None)
    ]
    state["frame_set"] = sorted(frame_names)
    # Masks affect collision; include a compact fingerprint, not pygame objects.
    mask = getattr(entity, "mask", None)
    if mask:
        from hashlib import sha256

        state["mask_hash"] = sha256(pg.image.tostring(mask.to_surface(), "RGBA")).hexdigest()
    state.update(
        id=entity.lab_id,
        kind=entity.lab_kind,
        row=entity.lab_row,
        col=getattr(entity, "lab_col", None),
        owner_id=getattr(entity, "lab_owner", None),
    )
    state["last_damage_source"] = getattr(entity, "lab_last_damage_source", None)
    state["modifiers"] = getattr(entity, "lab_modifiers", [])
    state["base_damage"] = getattr(entity, "lab_base_damage", None)
    # Composite fields used by the enabled upstream attacks (not pygame groups/maps).
    for key in ("orig_pos", "hit_zombies", "attack_zombies"):
        value = getattr(entity, key, None)
        if isinstance(value, (list, tuple, set)):
            state[key] = [getattr(item, "lab_id", item) for item in value]
    state["invulnerable"] = math.isinf(getattr(entity, "health", 0))
    state["hp"] = state.pop("health", None)
    if getattr(entity, "lab_parameters", None):
        state["parameters"] = entity.lab_parameters
    return state


def build_checkpoint(session):
    return clean(
        dict(
            tick=session.tick,
            sun=session.sun,
            cooldowns=session.cooldowns,
            next_natural_sun=session.next_natural_sun,
            wave=session.wave,
            status=session.status,
            schedule_index=session.schedule_index,
            pending_environment=session.schedule[session.schedule_index :],
            entity_counter=session.entity_counter,
            last_submit_ms=session.last_submit_ms,
            queue=list(session.queue),
            game_rng=session.game_rng.getstate(),
            command_receipts=session.commands,
            command_payloads=session.command_payloads,
            occupancy=session.level.map.map,
            entities=[
                entity_state(obj) for obj in session.entities.values() if not obj.lab_removed
            ],
        )
    )
