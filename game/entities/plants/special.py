"""Original pypvz entity behavior, grouped by responsibility. See docs/UPSTREAM.md."""
import pygame as pg
from game import constants as c
from game.entities.projectiles import Bullet
from game.entities.plants.base import Plant


class Chomper(Plant):
    def __init__(self, x, y):
        Plant.__init__(self, x, y, c.CHOMPER, c.PLANT_HEALTH, None)
        self.animate_interval = 140
        self.digest_timer = 0
        self.digest_interval = 15000
        self.attack_zombie = None
        self.zombie_group = None
        self.should_diggest = False

    def loadImages(self, name, scale):
        self.idle_frames = []
        self.attack_frames = []
        self.digest_frames = []
        self.animate_interval = 100  # 本身动画播放较慢

        idle_name = name
        attack_name = name + "Attack"
        digest_name = name + "Digest"

        frame_list = [self.idle_frames, self.attack_frames, self.digest_frames]
        name_list = [idle_name, attack_name, digest_name]
        scale_list = [1, 1, 1]
        # rect_list = [(0, 0, 100, 114), None, None]

        for i, name in enumerate(name_list):
            self.loadFrames(frame_list[i], name, scale_list[i])

        self.frames = self.idle_frames

    def canAttack(self, zombie):
        if (zombie.name in {c.POLE_VAULTING_ZOMBIE}) and (not zombie.jumped):
            return False
        if (zombie.name == c.SNORKELZOMBIE) and (zombie.frames == zombie.swim_frames):
            return False
        elif (
            self.state == c.IDLE
            and zombie.state != c.DIGEST
            and self.rect.x <= zombie.rect.centerx
            and (not zombie.losthead)
            and (self.rect.x + c.GRID_X_SIZE * 2.7 >= zombie.rect.centerx)
        ):
            return True
        return False

    def setIdle(self):
        self.state = c.IDLE
        self.changeFrames(self.idle_frames)

    def setAttack(self, zombie, zombie_group):
        self.attack_zombie = zombie
        self.zombie_group = zombie_group
        self.state = c.ATTACK
        self.changeFrames(self.attack_frames)

    def setDigest(self):
        self.state = c.DIGEST
        self.changeFrames(self.digest_frames)

    def attacking(self):
        if self.frame_index == (self.frame_num - 3):
            # 对活着的僵尸才需要吞下去消化
            if self.attack_zombie.alive():
                if not self.should_diggest:
                    # 播放吞的音效 由于一帧在这个循环中执行了若干次，可能被设置播放若干次导致声音重叠，所以用if保护
                    # 在尚未检测到需要消化时播放音效
                    c.SOUND_BIGCHOMP.play()
                    self.should_diggest = True
                    self.attack_zombie.kill()
        if (self.frame_index + 1) == self.frame_num:
            if self.should_diggest:
                self.setDigest()
                self.should_diggest = False
            else:
                self.setIdle()

    def digest(self):
        if self.digest_timer == 0:
            self.digest_timer = self.current_time
        elif (self.current_time - self.digest_timer) > self.digest_interval:
            self.digest_timer = 0
            self.setIdle()


class Squash(Plant):
    def __init__(self, x, y, map_plant_set):
        Plant.__init__(self, x, y, c.SQUASH, c.PLANT_HEALTH, None)
        self.orig_pos = (x, y)
        self.aim_timer = 0
        self.start_boom = False  # 和灰烬等植物统一变量名，在这里表示倭瓜是否跳起
        self.map_plant_set = map_plant_set

    def loadImages(self, name, scale):
        self.idle_frames = []
        self.aim_frames = []
        self.attack_frames = []

        idle_name = name
        aim_name = name + "Aim"
        attack_name = name + "Attack"

        frame_list = [self.idle_frames, self.aim_frames, self.attack_frames]
        name_list = [idle_name, aim_name, attack_name]

        for i, name in enumerate(name_list):
            self.loadFrames(frame_list[i], name)

        self.frames = self.idle_frames

    def canAttack(self, zombie):
        # 普通状态
        if (
            self.state == c.IDLE
            and self.rect.x <= zombie.rect.right
            and (self.rect.right + c.GRID_X_SIZE >= zombie.rect.x)
        ):
            return True
        # 攻击状态
        elif self.state == c.ATTACK:
            if pg.sprite.collide_rect_ratio(0.5)(zombie, self) or pg.sprite.collide_mask(
                zombie, self
            ):
                return True
        return False

    def setAttack(self, zombie, zombie_group):
        self.attack_zombie = zombie
        self.zombie_group = zombie_group
        self.state = c.ATTACK
        # 攻击状态下生命值无敌
        self.health = c.INF

    def attacking(self):
        if self.start_boom:
            if (self.frame_index + 1) == self.frame_num:
                for zombie in self.zombie_group:
                    if self.canAttack(zombie):
                        zombie.setDamage(1800, damage_type=c.ZOMBIE_RANGE_DAMAGE)
                self.health = 0  # 避免僵尸在原位啃食
                self.map_plant_set.remove(c.SQUASH)
                self.kill()
                # 播放碾压音效
                c.SOUND_SQUASHING.play()
        elif self.aim_timer == 0:
            # 锁定目标时播放音效
            c.SOUND_SQUASH_HMM.play()
            self.aim_timer = self.current_time
            self.changeFrames(self.aim_frames)
        elif (self.current_time - self.aim_timer) > 1000:
            self.changeFrames(self.attack_frames)
            self.rect.centerx = self.attack_zombie.rect.centerx
            self.start_boom = True
            self.animate_interval = 300

    def getPosition(self):
        return self.orig_pos


class Spikeweed(Plant):
    def __init__(self, x, y):
        Plant.__init__(self, x, y, c.SPIKEWEED, c.PLANT_HEALTH, None, scale=0.9)
        self.animate_interval = 70
        self.attack_timer = 0

    def setIdle(self):
        self.animate_interval = 70
        self.state = c.IDLE

    def canAttack(self, zombie):
        # 地刺能不能扎的判据：
        # 僵尸中心与地刺中心的距离或僵尸包括了地刺中心和右端（平衡得到合理的攻击范围,"僵尸包括了地刺中心和右端"是为以后巨人做准备）
        # 暂时不能用碰撞判断，平衡性不好
        if (-40 <= zombie.rect.centerx - self.rect.centerx <= 40) or (
            zombie.rect.left <= self.rect.x <= zombie.rect.right
            and zombie.rect.left <= self.rect.right <= zombie.rect.right
        ):
            return True
        return False

    def setAttack(self, zombie_group):
        self.zombie_group = zombie_group
        self.animate_interval = 35
        self.state = c.ATTACK
        if self.hit_timer != 0:
            self.hit_timer = self.current_time - 500

    def attacking(self):
        if self.hit_timer == 0:
            self.hit_timer = self.current_time - 500
        elif (self.current_time - self.attack_timer) >= 700:
            self.attack_timer = self.current_time
            # 最后再来判断攻击是否要杀死自己
            killSelf = False
            for zombie in self.zombie_group:
                if self.canAttack(zombie):
                    # 有车的僵尸
                    if zombie.name in {c.ZOMBONI}:
                        zombie.health = zombie.losthead_health
                        killSelf = True
                    else:
                        zombie.setDamage(20, damage_type=c.ZOMBIE_COMMON_DAMAGE)
            if killSelf:
                self.health = 0
            # 播放攻击音效，同子弹打击
            c.SOUND_BULLET_EXPLODE.play()


class HypnoShroom(Plant):
    def __init__(self, x, y):
        Plant.__init__(self, x, y, c.HYPNOSHROOM, c.PLANT_HEALTH, None)
        self.animate_interval = 80
        self.zombie_to_hypno = None
        self.attack_check = c.CHECK_ATTACK_NEVER

    def loadImages(self, name, scale):
        self.idle_frames = []
        self.sleep_frames = []

        idle_name = name
        sleep_name = name + "Sleep"

        frame_list = [self.idle_frames, self.sleep_frames]
        name_list = [idle_name, sleep_name]

        for i, name in enumerate(name_list):
            self.loadFrames(frame_list[i], name)

        self.frames = self.idle_frames

    def idling(self):
        if self.health < c.PLANT_HEALTH and self.zombie_to_hypno:
            self.health = 0


class LilyPad(Plant):
    def __init__(self, x, y):
        Plant.__init__(self, x, y, c.LILYPAD, c.PLANT_HEALTH, None)
        self.attack_check = c.CHECK_ATTACK_NEVER


class TorchWood(Plant):
    def __init__(self, x, y, bullet_group):
        Plant.__init__(self, x, y, c.TORCHWOOD, c.PLANT_HEALTH, bullet_group)
        self.attack_check = c.CHECK_ATTACK_NEVER

    def idling(self):
        for i in self.bullet_group:
            if (
                i.name == c.BULLET_PEA
                and i.passed_torchwood_x != self.rect.centerx
                and abs(i.rect.centerx - self.rect.centerx) <= 20
            ):
                self.bullet_group.add(
                    Bullet(
                        i.rect.x,
                        i.rect.y,
                        i.dest_y,
                        c.BULLET_FIREBALL,
                        c.BULLET_DAMAGE_FIREBALL_BODY,
                        effect=c.BULLET_EFFECT_UNICE,
                        passed_torchwood_x=self.rect.centerx,
                    )
                )
                i.kill()
            elif (
                i.name == c.BULLET_PEA_ICE
                and i.passed_torchwood_x != self.rect.centerx
                and abs(i.rect.centerx - self.rect.centerx)
            ):
                self.bullet_group.add(
                    Bullet(
                        i.rect.x,
                        i.rect.y,
                        i.dest_y,
                        c.BULLET_PEA,
                        c.BULLET_DAMAGE_NORMAL,
                        effect=None,
                        passed_torchwood_x=self.rect.centerx,
                    )
                )
                i.kill()


class CoffeeBean(Plant):
    def __init__(self, x, y, plant_group, map_content, map, map_x):
        Plant.__init__(self, x, y, c.COFFEEBEAN, c.PLANT_HEALTH, None)
        self.plant_group = plant_group
        self.map_content = map_content
        self.map = map
        self.map_x = map_x
        self.attack_check = c.CHECK_ATTACK_NEVER

    def animation(self):
        if (self.current_time - self.animate_timer) > self.animate_interval:
            self.frame_index += 1

            if self.frame_index >= self.frame_num:
                self.map_content[c.MAP_SLEEP] = False
                for plant in self.plant_group:
                    if plant.name in c.CAN_SLEEP_PLANTS:
                        if plant.state == c.SLEEP:
                            plant_map_x, _ = self.map.getMapIndex(
                                plant.rect.centerx, plant.rect.bottom
                            )
                            if plant_map_x == self.map_x:
                                plant.state = c.IDLE
                                plant.setIdle()
                                plant.changeFrames(plant.idle_frames)
                # 播放唤醒音效
                c.SOUND_MUSHROOM_WAKEUP.play()
                self.map_content[c.MAP_PLANT].remove(self.name)
                self.kill()
                self.frame_index = self.frame_num - 1

            self.animate_timer = self.current_time

        self.image = self.frames[self.frame_index]
        self.mask = pg.mask.from_surface(self.image)
        if self.current_time - self.highlight_time < 100:
            self.image.set_alpha(150)
        elif (self.current_time - self.hit_timer) < 200:
            self.image.set_alpha(192)
        else:
            self.image.set_alpha(255)


class TangleKlep(Plant):
    def __init__(self, x, y):
        Plant.__init__(self, x, y, c.TANGLEKLEP, c.PLANT_HEALTH, None)
        self.load_images()
        self.splashing = False

    def load_images(self):
        self.idle_frames = []
        self.splash_frames = []

        idle_name = self.name
        splash_name = self.name + "Splash"

        frame_list = [self.idle_frames, self.splash_frames]
        name_list = [idle_name, splash_name]

        for i, name in enumerate(name_list):
            self.loadFrames(frame_list[i], name)

        self.frames = self.idle_frames

    def canAttack(self, zombie):
        if zombie.state != c.DIE and (not zombie.losthead):
            # 这里碰撞应当比碰撞一般更容易，就设置成圆形或矩形模式，不宜采用mask
            if pg.sprite.collide_rect_ratio(1)(zombie, self):
                return True
        return False

    def setAttack(self, zombie, zombie_group):
        self.attack_zombie = zombie
        self.zombie_group = zombie_group
        self.state = c.ATTACK

    def attacking(self):
        if not self.splashing:
            self.splashing = True
            self.changeFrames(self.splash_frames)
            self.attack_zombie.kill()
            # 播放拖拽音效
            c.SOUND_TANGLE_KELP_DRAG.play()
        # 这里必须用elif排除尚未进入splash阶段，以免误触
        elif (self.frame_index + 1) >= self.frame_num:
            self.health = 0


class GraveBuster(Plant):
    def __init__(self, x, y, plant_group, map, map_x):
        Plant.__init__(self, x, y, c.GRAVEBUSTER, c.PLANT_HEALTH, None)
        self.map = map
        self.map_x = map_x
        self.plant_group = plant_group
        self.animate_interval = 100
        self.attack_check = c.CHECK_ATTACK_NEVER
        # 播放吞噬音效
        c.SOUND_GRAVEBUSTER_CHOMP.play()

    def animation(self):
        if (self.current_time - self.animate_timer) > self.animate_interval:
            self.frame_index += 1
            if self.frame_index >= self.frame_num:
                self.frame_index = self.frame_num - 1
                for item in self.plant_group:
                    if item.name == c.GRAVE:
                        item_map_x, _ = self.map.getMapIndex(item.rect.centerx, item.rect.bottom)
                        if item_map_x == self.map_x:
                            item.health = 0
                            self.health = 0
            self.animate_timer = self.current_time

        self.image = self.frames[self.frame_index]
        self.mask = pg.mask.from_surface(self.image)

        if self.current_time - self.highlight_time < 100:
            self.image.set_alpha(150)
        elif (self.current_time - self.hit_timer) < 200:
            self.image.set_alpha(192)
        else:
            self.image.set_alpha(255)


class Garlic(Plant):
    def __init__(self, x, y):
        Plant.__init__(self, x, y, c.GARLIC, c.GARLIC_HEALTH, None)
        self.load_images()
        self.cracked1 = False
        self.cracked2 = False

    def load_images(self):
        self.cracked1_frames = []
        self.cracked2_frames = []

        cracked1_frames_name = self.name + "_cracked1"
        cracked2_frames_name = self.name + "_cracked2"

        self.loadFrames(self.cracked1_frames, cracked1_frames_name)
        self.loadFrames(self.cracked2_frames, cracked2_frames_name)

    def idling(self):
        if (not self.cracked1) and self.health <= c.GARLIC_CRACKED1_HEALTH:
            self.changeFrames(self.cracked1_frames)
            self.cracked1 = True
        elif (not self.cracked2) and self.health <= c.GARLIC_CRACKED2_HEALTH:
            self.changeFrames(self.cracked2_frames)
            self.cracked2 = True
