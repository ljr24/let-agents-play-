"""Entity lifecycle and damage hooks, without experiment scheduling."""
import pygame as pg


def health(entity):
    return {
        key: getattr(entity, key, 0) for key in ("health", "helmet_health", "helmet_type2_health")
    }


class PlantDamage:
    def setDamage(self, damage, attacker):
        before = health(self)
        super().setDamage(damage, attacker)
        self.lab.damage(self, before, attacker.lab_id)


class ZombieDamage:
    def setDamage(self, *args, **kwargs):
        before = health(self)
        super().setDamage(*args, **kwargs)
        self.lab.damage(self, before, self.lab.source_id)


class TrackedGroup(pg.sprite.Group):
    def __init__(self, lab, kind, row=None):
        super().__init__()
        self.lab, self.kind, self.row = lab, kind, row

    def add_internal(self, sprite, layer=None):
        super().add_internal(sprite)
        if not hasattr(sprite, "lab_id"):
            self.lab.register(sprite, self.kind, self.row)

    def remove_internal(self, sprite):
        super().remove_internal(sprite)
        self.lab.removed(sprite)
