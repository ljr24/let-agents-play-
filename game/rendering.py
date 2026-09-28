"""Draw order and visible-pixel filtering kept together; neither advances the game."""
import pygame as pg
from . import assets as tool, constants as c


def draw(world, surface):
    background = tool.GFX[c.BACKGROUND_NAME][c.BACKGROUND_DAY]
    surface.blit(background, (0, 0), (c.BACKGROUND_OFFSET_X, 0, *c.SCREEN_SIZE))
    for row in range(5):
        world.terrain_groups[row].draw(surface)
        for group in (world.plant_groups[row], world.zombie_groups[row], world.bullet_groups[row]):
            for obj in group:
                surface.blit(obj.image, obj.rect)
        if world.cars[row]:
            world.cars[row].draw(surface)
    world.head_group.draw(surface)


def visible_entity_ids(world):
    """Use the actual drawing order and opaque pixels, not transparent sprite bounds."""
    visible_pixels = pg.mask.Mask((800, 575), fill=True)  # lower 25px are the UI footer
    for head in reversed(world.head_group.sprites()):
        visible_pixels.erase(pg.mask.from_surface(head.image), head.rect.topleft)
    draw_order = []
    for row in range(5):
        for group in (world.terrain_groups[row], world.plant_groups[row], world.zombie_groups[row], world.bullet_groups[row]):
            draw_order.extend(group.sprites())
        if world.cars[row]:
            draw_order.append(world.cars[row])
    ids = set()
    for obj in reversed(draw_order):
        display_mask = pg.mask.from_surface(obj.image)
        if visible_pixels.overlap(display_mask, obj.rect.topleft) is not None:
            ids.add(obj.lab_id)
        visible_pixels.erase(display_mask, obj.rect.topleft)
    return ids
