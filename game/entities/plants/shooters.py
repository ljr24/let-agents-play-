"""Original pypvz entity behavior, grouped by responsibility. See docs/UPSTREAM.md."""
import pygame as pg
from game import constants as c
from game.entities.projectiles import Bullet
from game.entities.projectiles import Fume
from game.entities.plants.base import Plant
from game.entities.projectiles import StarBullet


class PeaShooter(Plant):
    def __init__(self, x, y, bullet_group):
        Plant.__init__(self, x, y, c.PEASHOOTER, c.PLANT_HEALTH, bullet_group)
        self.shoot_timer = 0

    def attacking(self):
        if self.shoot_timer == 0:
            self.shoot_timer = self.current_time - 700
        elif (self.current_time - self.shoot_timer) >= 1400:
            self.bullet_group.add(
                Bullet(
                    self.rect.right - 15,
                    self.rect.y,
                    self.rect.y,
                    c.BULLET_PEA,
                    c.BULLET_DAMAGE_NORMAL,
                    effect=None,
                )
            )
            self.shoot_timer = self.current_time
            # 播放发射音效
            c.SOUND_SHOOT.play()

    def setAttack(self):
        self.state = c.ATTACK
        if self.shoot_timer != 0:
            self.shoot_timer = self.current_time - 700


class RepeaterPea(Plant):
    def __init__(self, x, y, bullet_group):
        Plant.__init__(self, x, y, c.REPEATERPEA, c.PLANT_HEALTH, bullet_group)
        self.shoot_timer = 0

        # 是否发射第一颗
        self.first_shot = False

    def attacking(self):
        if self.shoot_timer == 0:
            self.shoot_timer = self.current_time - 700
        elif self.current_time - self.shoot_timer >= 1400:
            self.first_shot = True
            self.bullet_group.add(
                Bullet(
                    self.rect.right - 15,
                    self.rect.y,
                    self.rect.y,
                    c.BULLET_PEA,
                    c.BULLET_DAMAGE_NORMAL,
                    effect=None,
                )
            )
            self.shoot_timer = self.current_time
            # 播放发射音效
            c.SOUND_SHOOT.play()
        elif self.first_shot and (self.current_time - self.shoot_timer) > 100:
            self.first_shot = False
            self.bullet_group.add(
                Bullet(
                    self.rect.right - 15,
                    self.rect.y,
                    self.rect.y,
                    c.BULLET_PEA,
                    c.BULLET_DAMAGE_NORMAL,
                    effect=None,
                )
            )
            # 播放发射音效
            c.SOUND_SHOOT.play()

    def setAttack(self):
        self.state = c.ATTACK
        if self.shoot_timer != 0:
            self.shoot_timer = self.current_time - 700


class ThreePeaShooter(Plant):
    def __init__(self, x, y, bullet_groups, map_y, background_type):
        Plant.__init__(self, x, y, c.THREEPEASHOOTER, c.PLANT_HEALTH, None)
        self.shoot_timer = 0
        self.map_y = map_y
        self.bullet_groups = bullet_groups
        self.background_type = background_type

    def attacking(self):
        if self.shoot_timer == 0:
            self.shoot_timer = self.current_time - 700
        if (self.current_time - self.shoot_timer) >= 1400:
            offset_y = 9  # modify bullet in the same y position with bullets of other plants
            for i in range(3):
                tmp_y = self.map_y + (i - 1)
                if self.background_type in c.POOL_EQUIPPED_BACKGROUNDS:
                    if tmp_y < 0 or tmp_y >= c.GRID_POOL_Y_LEN:
                        continue
                else:
                    if tmp_y < 0 or tmp_y >= c.GRID_Y_LEN:
                        continue
                if self.background_type in {
                    c.BACKGROUND_POOL,
                    c.BACKGROUND_FOG,
                    c.BACKGROUND_ROOF,
                    c.BACKGROUND_ROOFNIGHT,
                }:
                    dest_y = self.rect.y + (i - 1) * c.GRID_POOL_Y_SIZE + offset_y
                else:
                    dest_y = self.rect.y + (i - 1) * c.GRID_Y_SIZE + offset_y
                self.bullet_groups[tmp_y].add(
                    Bullet(
                        self.rect.right - 15,
                        self.rect.y,
                        dest_y,
                        c.BULLET_PEA,
                        c.BULLET_DAMAGE_NORMAL,
                        effect=None,
                    )
                )
            self.shoot_timer = self.current_time
            # 播放发射音效
            c.SOUND_SHOOT.play()

    def setAttack(self):
        self.state = c.ATTACK
        if self.shoot_timer != 0:
            self.shoot_timer = self.current_time - 700


class SnowPeaShooter(Plant):
    def __init__(self, x, y, bullet_group):
        Plant.__init__(self, x, y, c.SNOWPEASHOOTER, c.PLANT_HEALTH, bullet_group)
        self.shoot_timer = 0

    def attacking(self):
        if self.shoot_timer == 0:
            self.shoot_timer = self.current_time - 700
        elif (self.current_time - self.shoot_timer) >= 1400:
            self.bullet_group.add(
                Bullet(
                    self.rect.right - 15,
                    self.rect.y,
                    self.rect.y,
                    c.BULLET_PEA_ICE,
                    c.BULLET_DAMAGE_NORMAL,
                    effect=c.BULLET_EFFECT_ICE,
                )
            )
            self.shoot_timer = self.current_time
            # 播放发射音效
            c.SOUND_SHOOT.play()
            # 播放冰子弹音效
            c.SOUND_SNOWPEA_SPARKLES.play()

    def setAttack(self):
        self.state = c.ATTACK
        if self.shoot_timer != 0:
            self.shoot_timer = self.current_time - 700


class StarFruit(Plant):
    def __init__(self, x, y, bullet_group, level):
        Plant.__init__(self, x, y, c.STARFRUIT, c.PLANT_HEALTH, bullet_group)
        self.shoot_timer = 0
        self.level = level
        self.map_x, self.map_y = self.level.map.getMapIndex(x, y)

    def canAttack(self, zombie):
        if (zombie.name == c.SNORKELZOMBIE) and (zombie.frames == zombie.swim_frames):
            return False
        if zombie.state != c.DIE:
            zombie_map_y = self.level.map.getMapIndex(zombie.rect.centerx, zombie.rect.bottom)[1]
            if (self.rect.x >= zombie.rect.x) and (self.map_y == zombie_map_y):  # 对于同行且在杨桃后的僵尸
                return True
            # 斜向上，理想直线方程为：
            # f(zombie.rect.x) = -0.75*(zombie.rect.x - (self.rect.right - 5)) + self.rect.y - 10
            # 注意实际上为射线
            elif (
                -100
                <= (
                    zombie.rect.y
                    - (-0.75 * (zombie.rect.x - (self.rect.right - 5)) + self.rect.y - 10)
                )
                <= 70
                and (zombie.rect.left <= c.SCREEN_WIDTH)
                and (zombie.rect.x >= self.rect.x)
            ):
                return True
            # 斜向下，理想直线方程为：f(zombie.rect.x) = zombie.rect.x + self.rect.y - self.rect.right - 15
            # 注意实际上为射线
            elif (
                abs(zombie.rect.y - (zombie.rect.x + self.rect.y - self.rect.right - 15)) <= 70
                and (zombie.rect.left <= c.SCREEN_WIDTH)
                and (zombie.rect.x >= self.rect.x)
            ):
                return True
            elif zombie.rect.left <= self.rect.x <= zombie.rect.right:
                return True
        return False

    def attacking(self):
        if self.shoot_timer == 0:
            self.shoot_timer = self.current_time - 700
        elif (self.current_time - self.shoot_timer) >= 1400:
            # pypvz特有设定：向后打的杨桃子弹无视铁门与报纸防具
            self.bullet_group.add(
                StarBullet(
                    self.rect.left - 10,
                    self.rect.y + 15,
                    c.BULLET_DAMAGE_NORMAL,
                    c.STAR_BACKWARD,
                    self.level,
                    damage_type=c.ZOMBIE_COMMON_DAMAGE,
                )
            )
            # 其他方向的杨桃子弹伤害效果与豌豆等同
            self.bullet_group.add(
                StarBullet(
                    self.rect.centerx - 20,
                    self.rect.bottom - self.rect.h - 15,
                    c.BULLET_DAMAGE_NORMAL,
                    c.STAR_UPWARD,
                    self.level,
                )
            )
            self.bullet_group.add(
                StarBullet(
                    self.rect.centerx - 20,
                    self.rect.bottom - 5,
                    c.BULLET_DAMAGE_NORMAL,
                    c.STAR_DOWNWARD,
                    self.level,
                )
            )
            self.bullet_group.add(
                StarBullet(
                    self.rect.right - 5,
                    self.rect.bottom - 20,
                    c.BULLET_DAMAGE_NORMAL,
                    c.STAR_FORWARD_DOWN,
                    self.level,
                )
            )
            self.bullet_group.add(
                StarBullet(
                    self.rect.right - 5,
                    self.rect.y - 10,
                    c.BULLET_DAMAGE_NORMAL,
                    c.STAR_FORWARD_UP,
                    self.level,
                )
            )
            self.shoot_timer = self.current_time
            # 播放发射音效
            c.SOUND_SHOOT.play()

    def setAttack(self):
        self.state = c.ATTACK
        if self.shoot_timer != 0:
            self.shoot_timer = self.current_time - 700


class PuffShroom(Plant):
    def __init__(self, x, y, bullet_group):
        Plant.__init__(self, x, y, c.PUFFSHROOM, c.PLANT_HEALTH, bullet_group)
        self.shoot_timer = 0

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

    def attacking(self):
        if self.shoot_timer == 0:
            self.shoot_timer = self.current_time - 700
        elif (self.current_time - self.shoot_timer) >= 1400:
            self.bullet_group.add(
                Bullet(
                    self.rect.right,
                    self.rect.y + 10,
                    self.rect.y + 10,
                    c.BULLET_MUSHROOM,
                    c.BULLET_DAMAGE_NORMAL,
                    effect=None,
                )
            )
            self.shoot_timer = self.current_time
            # 播放音效
            c.SOUND_PUFF.play()

    def canAttack(self, zombie):
        if (zombie.name == c.SNORKELZOMBIE) and (zombie.frames == zombie.swim_frames):
            return False
        if (
            self.rect.x <= zombie.rect.right
            and (self.rect.x + c.GRID_X_SIZE * 4 >= zombie.rect.x)
            and (zombie.rect.left <= c.SCREEN_WIDTH + 10)
        ):
            return True
        return False

    def setAttack(self):
        self.state = c.ATTACK
        if self.shoot_timer != 0:
            self.shoot_timer = self.current_time - 700


class ScaredyShroom(Plant):
    def __init__(self, x, y, bullet_group):
        Plant.__init__(self, x, y, c.SCAREDYSHROOM, c.PLANT_HEALTH, bullet_group)
        self.shoot_timer = 0
        self.cry_x_range = c.GRID_X_SIZE * 1.5

    def loadImages(self, name, scale):
        self.idle_frames = []
        self.cry_frames = []
        self.sleep_frames = []

        idle_name = name
        cry_name = name + "Cry"
        sleep_name = name + "Sleep"

        frame_list = [self.idle_frames, self.cry_frames, self.sleep_frames]
        name_list = [idle_name, cry_name, sleep_name]

        for i, name in enumerate(name_list):
            self.loadFrames(frame_list[i], name)

        self.frames = self.idle_frames

    def needCry(self, zombie):
        if zombie.state != c.DIE and abs(self.rect.x - zombie.rect.x) < self.cry_x_range:
            return True
        return False

    def setCry(self):
        self.state = c.CRY
        self.changeFrames(self.cry_frames)

    def setAttack(self):
        self.state = c.ATTACK
        self.changeFrames(self.idle_frames)
        if self.shoot_timer != 0:
            self.shoot_timer = self.current_time - 700

    def setIdle(self):
        self.state = c.IDLE
        self.changeFrames(self.idle_frames)

    def attacking(self):
        if self.shoot_timer == 0:
            self.shoot_timer = self.current_time - 700
        elif (self.current_time - self.shoot_timer) >= 1400:
            self.bullet_group.add(
                Bullet(
                    self.rect.right - 15,
                    self.rect.y + 40,
                    self.rect.y + 40,
                    c.BULLET_MUSHROOM,
                    c.BULLET_DAMAGE_NORMAL,
                    effect=None,
                )
            )
            self.shoot_timer = self.current_time
            # 播放音效
            c.SOUND_PUFF.play()


class SeaShroom(Plant):
    def __init__(self, x, y, bullet_group):
        Plant.__init__(self, x, y, c.SEASHROOM, c.PLANT_HEALTH, bullet_group)
        self.shoot_timer = 0

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

    def attacking(self):
        if self.shoot_timer == 0:
            self.shoot_timer = self.current_time - 700
        elif (self.current_time - self.shoot_timer) >= 1400:
            self.bullet_group.add(
                Bullet(
                    self.rect.right,
                    self.rect.y + 50,
                    self.rect.y + 50,
                    c.BULLET_SEASHROOM,
                    c.BULLET_DAMAGE_NORMAL,
                    effect=None,
                )
            )
            self.shoot_timer = self.current_time
            # 播放发射音效
            c.SOUND_PUFF.play()

    def canAttack(self, zombie):
        if (zombie.name == c.SNORKELZOMBIE) and (zombie.frames == zombie.swim_frames):
            return False
        if (
            self.rect.x <= zombie.rect.right
            and (self.rect.x + c.GRID_X_SIZE * 4 >= zombie.rect.x)
            and (zombie.rect.left <= c.SCREEN_WIDTH + 10)
        ):
            return True
        return False

    def setAttack(self):
        self.state = c.ATTACK
        if self.shoot_timer != 0:
            self.shoot_timer = self.current_time - 700


class FumeShroom(Plant):
    def __init__(self, x, y, bullet_group, zombie_group):
        Plant.__init__(self, x, y, c.FUMESHROOM, c.PLANT_HEALTH, bullet_group)
        self.shoot_timer = 0
        self.show_attack_frames = True
        self.zombie_group = zombie_group

    def loadImages(self, name, scale):
        self.idle_frames = []
        self.sleep_frames = []
        self.attack_frames = []

        idle_name = name
        sleep_name = name + "Sleep"
        attack_name = name + "Attack"

        frame_list = [self.idle_frames, self.sleep_frames, self.attack_frames]
        name_list = [idle_name, sleep_name, attack_name]

        for i, name in enumerate(name_list):
            self.loadFrames(frame_list[i], name)

        self.frames = self.idle_frames

    def canAttack(self, zombie):
        if (zombie.name == c.SNORKELZOMBIE) and (zombie.frames == zombie.swim_frames):
            return False
        if (
            self.rect.x <= zombie.rect.right
            and (self.rect.x + c.GRID_X_SIZE * 5 >= zombie.rect.x)
            and (zombie.rect.left <= c.SCREEN_WIDTH + 10)
        ):
            return True
        return False

    def setAttack(self):
        self.state = c.ATTACK
        if self.shoot_timer != 0:
            self.shoot_timer = self.current_time - 700

    def attacking(self):
        if self.shoot_timer == 0:
            self.shoot_timer = self.current_time - 700
        elif self.current_time - self.shoot_timer >= 1100:
            if self.show_attack_frames:
                self.show_attack_frames = False
                self.changeFrames(self.attack_frames)

        if self.current_time - self.shoot_timer >= 1400:
            self.bullet_group.add(Fume(self.rect.right - 35, self.rect.y))
            # 烟雾只是个动画，实际伤害由本身完成
            for target_zombie in self.zombie_group:
                if self.canAttack(target_zombie):
                    target_zombie.setDamage(
                        c.BULLET_DAMAGE_NORMAL,
                        damage_type=c.ZOMBIE_RANGE_DAMAGE,
                    )
            self.shoot_timer = self.current_time
            self.show_attack_frames = True
            # 播放发射音效
            c.SOUND_FUME.play()

    def animation(self):
        if (self.current_time - self.animate_timer) > self.animate_interval:
            self.frame_index += 1
            if self.frame_index >= self.frame_num:
                if self.frames == self.attack_frames:
                    self.changeFrames(self.idle_frames)
                else:
                    self.frame_index = 0
            self.animate_timer = self.current_time

        self.image = self.frames[self.frame_index]
        self.mask = pg.mask.from_surface(self.image)

        if self.current_time - self.highlight_time < 100:
            self.image.set_alpha(150)
        elif (self.current_time - self.hit_timer) < 200:
            self.image.set_alpha(192)
        else:
            self.image.set_alpha(255)
