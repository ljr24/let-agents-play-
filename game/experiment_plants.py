"""Small experiment adapters for target identity, deterministic clocks and attribution."""
from . import constants as c
from .entities.plants.base import Plant
from .entities.plants import special
from .entities.projectiles import Bullet
from .tracking import PlantDamage


class FirstShotClock:
    """Keep each upstream firing pattern, avoiding a zero-valued timer sentinel."""
    def setAttack(self):
        super().setAttack()
        self.shoot_timer = self.current_time - 700
        if self.shoot_timer == 0:
            self.shoot_timer = -1


class LabCoffee(PlantDamage, special.CoffeeBean):
    def animation(self):
        target = self.lab.entities.get(self.target_id)
        if target is None or target.lab_removed or target.state != c.SLEEP:
            self.lab_remove_reason = "target_lost"
            self.kill()
            return
        if self.current_time - self.animate_timer > self.animate_interval:
            if self.frame_index + 1 >= self.frame_num:
                target.setIdle()
                target.changeFrames(target.idle_frames)
                target.animate_timer = self.current_time
                self.map_content[c.MAP_SLEEP] = False
                self.lab.emit("plant_awakened", plant_id=target.lab_id, coffee_id=self.lab_id)
                c.SOUND_MUSHROOM_WAKEUP.play()
                self.lab_remove_reason = "consumed"
                self.kill()
                return
        Plant.animation(self)


class LabTorch(PlantDamage, special.TorchWood):
    def idling(self):
        for old in list(self.bullet_group):
            if (getattr(old, "state", None) != c.FLY
                    or getattr(old, "passed_torchwood_x", None) == self.rect.centerx
                    or abs(old.rect.centerx - self.rect.centerx) > 20):
                continue
            if old.name not in (c.BULLET_PEA, c.BULLET_PEA_ICE):
                continue
            fire = old.name == c.BULLET_PEA
            new = Bullet(old.rect.x, old.rect.y, old.dest_y,
                         c.BULLET_FIREBALL if fire else c.BULLET_PEA,
                         c.BULLET_DAMAGE_FIREBALL_BODY if fire else c.BULLET_DAMAGE_NORMAL,
                         effect=c.BULLET_EFFECT_UNICE if fire else None,
                         passed_torchwood_x=self.rect.centerx)
            new.lab_owner = old.lab_owner
            new.lab_base_damage = getattr(old, "lab_base_damage", c.BULLET_DAMAGE_NORMAL)
            new.lab_modifiers = [*getattr(old, "lab_modifiers", []), self.lab_id]
            self.bullet_group.add(new)
            self.lab.emit("bullet_transformed", old_bullet_id=old.lab_id, bullet_id=new.lab_id,
                          plant_id=new.lab_owner, modifier_id=self.lab_id,
                          before_type=old.name, after_type=new.name)
            old.kill()
