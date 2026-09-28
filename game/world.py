"""Battlefield owns entities, occupancy, and battle updates; not actions, resources, or menus."""
from contextlib import contextmanager
import pygame as pg
from . import constants as c, map as lawn
from .combat import CombatRules
from .content import create_plant, create_zombie
from .tracking import TrackedGroup, health
from .entities.props import Hole


class Battlefield(CombatRules):
    def __init__(self, lab):
        self.lab = lab
        self.background_type = c.BACKGROUND_DAY
        self.map = lawn.Map(self.background_type)
        self.map_x_len, self.map_y_len = 9, 5
        self.game_info = {c.CURRENT_TIME: 0}
        self.current_time = 0
        self.new_plant_and_positon = None
        self.sun_group = pg.sprite.Group()
        self.head_group = TrackedGroup(
            lab, "visual"
        )  # retained in checkpoints: can occlude visible enemies
        self.plant_groups = [TrackedGroup(lab, "plant", i) for i in range(5)]
        self.terrain_groups = [TrackedGroup(lab, "terrain", i) for i in range(5)]
        self.zombie_groups = [TrackedGroup(lab, "zombie", i) for i in range(5)]
        self.bullet_groups = [TrackedGroup(lab, "bullet", i) for i in range(5)]
        self.hypno_zombie_groups = [pg.sprite.Group() for _ in range(5)]
        self.setupCars()
        for row, car in enumerate(self.cars):
            lab.register(car, "mower", row)

    def create_plant(self, name, row, col):
        return create_plant(self, name, row, col)

    def commit_plant(self, obj, row, col):
        self.plant_groups[row].add(obj)
        sleeping = obj.state == c.SLEEP or self.map.map[row][col][c.MAP_SLEEP]
        self.map.addMapPlant(col, row, obj.name, sleep=sleeping)
        self.new_plant_and_positon = (obj.name, (col, row))

    def spawn(self, event):
        row = event["row"]
        obj = create_zombie(self, event)
        self.zombie_groups[row].add(obj)

    @contextmanager
    def source(self, entity):
        previous = self.lab.source_id
        self.lab.source_id = entity.lab_id
        try:
            yield
        finally:
            self.lab.source_id = previous

    def update_entities(self):
        self.current_time = self.game_info[c.CURRENT_TIME] = self.lab.ms
        updated = set()
        for row in range(5):
            for group in (self.terrain_groups[row], self.bullet_groups[row], self.plant_groups[row], self.zombie_groups[row]):
                for obj in list(group):
                    if obj.lab_removed or obj.lab_id in updated:
                        continue
                    updated.add(obj.lab_id)
                    before = health(obj)
                    with self.source(obj):
                        obj.update(self.game_info)
                    # Lost-head decay and self-consumption don't call setDamage.
                    if health(obj) != before:
                        self.lab.damage(obj, before, obj.lab_id, "decay_or_consumption")
                    if obj.lab_kind == "terrain" and obj.health <= 0:
                        self.map.removeMapPlant(obj.lab_col, row, c.HOLE)
                        self.lab.emit("terrain_changed", row=row, col=obj.lab_col, terrain="grass")
                        obj.kill()
            car = self.cars[row]
            if car:
                car.update(self.game_info)
        self.head_group.update(self.game_info)

    def checkBulletCollisions(self):
        for row in range(5):
            for bullet in self.bullet_groups[row]:
                if getattr(bullet, "state", None) != c.FLY:
                    continue
                for enemy in self.zombie_groups[row]:
                    if enemy.state != c.DIE and pg.sprite.collide_mask(enemy, bullet):
                        self.lab.emit(
                            "bullet_hit",
                            bullet_id=bullet.lab_id,
                            plant_id=bullet.lab_owner,
                            target_id=enemy.lab_id,
                        )
                        with self.source(bullet):
                            enemy.setDamage(
                                bullet.damage, effect=bullet.effect, damage_type=bullet.damage_type
                            )
                        bullet.setExplode()
                        break

    def checkPlant(self, obj, row):
        with self.source(obj):
            super().checkPlant(obj, row)

    def killPlant(self, obj, shovel=False):
        if obj.lab_removed:
            return
        consumed = obj.name in ("CherryBomb", "Jalapeno", "DoomShroom", "Squash", "PotatoMine") and getattr(obj, "start_boom", False)
        reason = "shovel" if shovel else "consumed" if consumed else "eaten"
        obj.lab_remove_reason = reason
        obj.health = 0
        obj.kill()

    def on_plant_removed(self, obj):
        row, col = obj.lab_row, obj.lab_col
        reason = getattr(obj, "lab_remove_reason", "consumed" if obj.name in ("CoffeeBean", "Squash") else "eaten")
        obj.lab_remove_reason = reason
        self.map.removeMapPlant(col, row, obj.name)
        if obj.name in c.CAN_SLEEP_PLANTS:
            self.map.map[row][col][c.MAP_SLEEP] = False
        self.lab.emit(
            "plant_loss",
            plant_id=obj.lab_id,
            plant_type=obj.name,
            row=obj.lab_row,
            col=obj.lab_col,
            reason=reason,
        )
        if obj.name == c.DOOMSHROOM and getattr(obj, "boomed", False):
            x, y = self.map.getMapGridPos(col, row)
            hole = Hole(x, y, self.map.map[row][col][c.MAP_PLOT_TYPE])
            hole.lab_col = col
            hole.timer = hole.current_time = hole.animate_timer = self.lab.ms
            self.map.map[row][col][c.MAP_PLANT].add(c.HOLE)
            self.terrain_groups[row].add(hole)
            self.lab.emit("terrain_changed", row=row, col=col, terrain="crater")

    def checkCarCollisions(self):
        for row, car in enumerate(self.cars):
            if car is None:
                continue
            for enemy in self.zombie_groups[row]:
                if enemy.health <= 0:
                    continue
                contact = pg.sprite.collide_mask(enemy, car)
                if contact and enemy.state != c.DIE and not enemy.losthead and car.state == c.IDLE:
                    car.setWalk()
                    self.lab.emit("mower_started", mower_id=car.lab_id, row=row)
                if contact or car.rect.x <= enemy.rect.right <= car.rect.right:
                    before = health(enemy)
                    enemy.health = 0
                    self.lab.damage(enemy, before, car.lab_id)
            if car.dead:
                self.lab.removed(car)
                self.cars[row] = None

    def collisions(self):
        self.checkBulletCollisions()
        self.checkZombieCollisions()
        self.checkPlants()
        self.checkCarCollisions()
        for group in self.zombie_groups:
            for obj in group:
                self.lab.audit_death(obj)

    def draw(self, surface):
        from .rendering import draw

        draw(self, surface)

    def visible_entity_ids(self):
        from .rendering import visible_entity_ids

        return visible_entity_ids(self)
