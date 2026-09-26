"""Battlefield owns entities, occupancy, and battle updates; not actions, resources, or menus."""
from contextlib import contextmanager
import pygame as pg
from . import constants as c, map as lawn
from .combat import CombatRules
from .content import create_plant, create_zombie
from .tracking import TrackedGroup, health


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
        self.map.addMapPlant(col, row, obj.name)
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
        for row in range(5):
            for group in (self.bullet_groups[row], self.plant_groups[row], self.zombie_groups[row]):
                for obj in list(group):
                    before = health(obj)
                    with self.source(obj):
                        obj.update(self.game_info)
                    # Lost-head decay and self-consumption don't call setDamage.
                    if health(obj) != before:
                        self.lab.damage(obj, before, obj.lab_id, "decay_or_consumption")
            car = self.cars[row]
            if car:
                car.update(self.game_info)
        self.head_group.update(self.game_info)

    def checkBulletCollisions(self):
        for row in range(5):
            for bullet in self.bullet_groups[row]:
                if bullet.state != c.FLY:
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
        reason = "shovel" if shovel else "consumed" if obj.name == "CherryBomb" else "eaten"
        obj.lab_remove_reason = reason
        self.map.removeMapPlant(obj.lab_col, obj.lab_row, obj.name)
        obj.health = 0
        self.lab.emit(
            "plant_loss",
            plant_id=obj.lab_id,
            plant_type=obj.name,
            row=obj.lab_row,
            col=obj.lab_col,
            reason=reason,
        )
        obj.kill()

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
