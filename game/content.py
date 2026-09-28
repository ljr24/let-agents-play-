"""Construction of experiment-enabled original entities and explicit day-lab timing overrides."""
from . import constants as c
from .entities.plants import economy, shooters, defense, explosives, special
from .entities.zombies import special as special_zombies
from .experiment_plants import FirstShotClock, LabCoffee, LabTorch
from .entities.zombies import walkers as zombie
from .entities.projectiles import Bullet
from .tracking import PlantDamage, ZombieDamage
from .catalog import PLANTS


class LabSunFlower(PlantDamage, economy.SunFlower):
    def idling(self):
        if self.current_time >= self.next_sun_ms:
            self.lab.pending_sun.append((self.lab_id, 25))
            self.next_sun_ms += 24000


class ShooterClock:
    """Keep upstream attacks, replacing the ambiguous zero first-shot sentinel."""

    def setAttack(self):
        self.state = c.ATTACK
        parameters = getattr(self, "lab_parameters", {})
        interval = parameters.get("shot_interval_ms", 1400)
        delay = parameters.get("first_shot_delay_ms", 700)
        self.shoot_timer = self.current_time - interval + delay
        if self.name == c.REPEATERPEA:
            self.first_shot = False

    def attacking(self):
        elapsed = self.current_time - self.shoot_timer
        first = elapsed >= getattr(self, "lab_parameters", {}).get("shot_interval_ms", 1400)
        second = self.name == c.REPEATERPEA and self.first_shot and elapsed > 100
        if not (first or second):
            return
        icy = self.name == c.SNOWPEASHOOTER
        self.bullet_group.add(
            Bullet(
                self.rect.right - 15,
                self.rect.y,
                self.rect.y,
                c.BULLET_PEA_ICE if icy else c.BULLET_PEA,
                c.BULLET_DAMAGE_NORMAL,
                effect=c.BULLET_EFFECT_ICE if icy else None,
            )
        )
        if first:
            self.shoot_timer = self.current_time
        if self.name == c.REPEATERPEA:
            self.first_shot = first
        c.SOUND_SHOOT.play()
        if icy:
            c.SOUND_SNOWPEA_SPARKLES.play()


PLANT_CLASSES = {
    "SunFlower": LabSunFlower,
    "Peashooter": type("LabPea", (ShooterClock, PlantDamage, shooters.PeaShooter), {}),
    "SnowPea": type("LabSnow", (ShooterClock, PlantDamage, shooters.SnowPeaShooter), {}),
    "RepeaterPea": type("LabRepeater", (ShooterClock, PlantDamage, shooters.RepeaterPea), {}),
    "WallNut": type("LabNut", (PlantDamage, defense.WallNut), {}),
    "CherryBomb": type("LabCherry", (PlantDamage, explosives.CherryBomb), {}),
    "TallNut": type("LabTallNut", (PlantDamage, defense.TallNut), {}),
    "Threepeater": type("LabThree", (FirstShotClock, PlantDamage, shooters.ThreePeaShooter), {}),
    "StarFruit": type("LabStar", (FirstShotClock, PlantDamage, shooters.StarFruit), {}),
    "ScaredyShroom": type("LabScaredy", (FirstShotClock, PlantDamage, shooters.ScaredyShroom), {}),
    "FumeShroom": type("LabFume", (FirstShotClock, PlantDamage, shooters.FumeShroom), {}),
    "TorchWood": LabTorch,
    "CoffeeBean": LabCoffee,
    "PotatoMine": type("LabPotato", (PlantDamage, explosives.PotatoMine), {}),
    "Jalapeno": type("LabJalapeno", (PlantDamage, explosives.Jalapeno), {}),
    "DoomShroom": type("LabDoom", (PlantDamage, explosives.DoomShroom), {}),
    "Squash": type("LabSquash", (PlantDamage, special.Squash), {}),
    "Spikeweed": type("LabSpike", (PlantDamage, special.Spikeweed), {}),
}
ZOMBIE_CLASSES = {
    name: type("Lab" + name, (ZombieDamage, cls), {})
    for name, cls in (
        ("Zombie", zombie.NormalZombie),
        ("ConeheadZombie", zombie.ConeHeadZombie),
        ("BucketheadZombie", zombie.BucketHeadZombie),
        ("FootballZombie", zombie.FootballZombie),
        ("FlagZombie", zombie.FlagZombie),
        ("NewspaperZombie", zombie.NewspaperZombie),
        ("ScreenDoorZombie", zombie.ScreenDoorZombie),
        ("PoleVaultingZombie", special_zombies.PoleVaultingZombie),
    )
}


def create_plant(world, name, row, col):
    x, y = world.map.getMapGridPos(col, row)
    spec, cls = PLANTS[name], PLANT_CLASSES[name]
    params = world.lab.config.plant_overrides.get(name, {})
    if spec.constructor == "economy":
        obj = cls(x, y, world.sun_group)
        obj.next_sun_ms = world.lab.ms + 6000
    elif spec.constructor == "shooter":
        obj = cls(x, y, world.bullet_groups[row])
        obj.shoot_timer = (
            world.lab.ms
            - params.get("shot_interval_ms", 1400)
            + params.get("first_shot_delay_ms", 700)
        )
    elif spec.constructor == "three":
        obj = cls(x, y, world.bullet_groups, row, world.background_type)
    elif spec.constructor == "star":
        obj = cls(x, y, world.bullet_groups[row], world)
    elif spec.constructor == "torch":
        obj = cls(x, y, world.bullet_groups[row])
    elif spec.constructor == "fume":
        obj = cls(x, y, world.bullet_groups[row], world.zombie_groups[row])
    elif spec.constructor == "coffee":
        obj = cls(x, y, world.plant_groups[row], world.map.map[row][col], world.map, col)
        obj.target_id = next(p.lab_id for p in world.plant_groups[row]
                             if p.lab_col == col and p.state == c.SLEEP)
    elif spec.constructor == "doom":
        obj = cls(x, y, world.map.map[row][col][c.MAP_PLANT], 2)
    elif name == "Squash":
        obj = cls(x, y, world.map.map[row][col][c.MAP_PLANT])
    else:
        obj = cls(x, y)
    obj.lab_parameters = dict(params)
    if "health" in params:
        obj.health = params["health"]
    obj.current_time = obj.animate_timer = world.lab.ms
    obj.hit_timer = obj.highlight_time = -1000
    obj.lab_col = col
    if name in ("FumeShroom", "ScaredyShroom", "DoomShroom"):
        obj.setSleep()
    if name == "PotatoMine":
        obj.init_timer = world.lab.ms or -1
    return obj


def create_zombie(world, event):
    row, name = event["row"], event["type"]
    obj = ZOMBIE_CLASSES[name](event["x"], world.map.getMapGridPos(0, row)[1], world.head_group)
    for key, value in world.lab.config.zombie_overrides.get(name, {}).items():
        setattr(obj, key, value)  # Whitelisted by catalog.validate_overrides before reset.
    obj.current_time = obj.walk_timer = obj.animate_timer = world.lab.ms
    return obj
