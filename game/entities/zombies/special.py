"""Original pypvz entity behavior, grouped by responsibility. See docs/UPSTREAM.md."""
import pygame as pg
from game import constants as c
from game.entities.zombies.base import Zombie


class DuckyTubeZombie(Zombie):
    def __init__(self, x, y, head_group):
        Zombie.__init__(self, x, y, c.DUCKY_TUBE_ZOMBIE, head_group, can_swim=True)

    def loadImages(self):
        self.walk_frames = []
        self.swim_frames = []
        self.attack_frames = []
        self.losthead_walk_frames = []
        self.losthead_attack_frames = []
        self.die_frames = []
        self.boomdie_frames = []

        walk_name = self.name
        swim_name = self.name + "Swim"
        attack_name = self.name + "Attack"
        losthead_walk_name = self.name + "LostHead"
        losthead_attack_name = self.name + "LostHead"
        die_name = self.name + "Die"
        boomdie_name = c.BOOMDIE

        frame_list = [
            self.walk_frames,
            self.swim_frames,
            self.attack_frames,
            self.losthead_walk_frames,
            self.losthead_attack_frames,
            self.die_frames,
            self.boomdie_frames,
        ]
        name_list = [
            walk_name,
            swim_name,
            attack_name,
            losthead_walk_name,
            losthead_attack_name,
            die_name,
            boomdie_name,
        ]

        for i, name in enumerate(name_list):
            self.loadFrames(frame_list[i], name)

        self.frames = self.walk_frames


class ConeHeadDuckyTubeZombie(Zombie):
    def __init__(self, x, y, head_group):
        Zombie.__init__(
            self,
            x,
            y,
            c.CONEHEAD_DUCKY_TUBE_ZOMBIE,
            head_group,
            helmet_health=c.CONEHEAD_HEALTH,
            can_swim=True,
        )

    def loadImages(self):
        self.helmet_walk_frames = []
        self.walk_frames = []
        self.helmet_swim_frames = []
        self.swim_frames = []
        self.helmet_attack_frames = []
        self.attack_frames = []
        self.losthead_walk_frames = []
        self.losthead_attack_frames = []
        self.die_frames = []
        self.boomdie_frames = []

        helmet_walk_name = self.name
        helmet_swim_name = self.name + "Swim"
        helmet_attack_name = self.name + "Attack"
        walk_name = c.DUCKY_TUBE_ZOMBIE
        swim_name = c.DUCKY_TUBE_ZOMBIE + "Swim"
        attack_name = c.DUCKY_TUBE_ZOMBIE + "Attack"
        losthead_walk_name = c.DUCKY_TUBE_ZOMBIE + "LostHead"
        losthead_attack_name = c.DUCKY_TUBE_ZOMBIE + "LostHead"
        die_name = c.DUCKY_TUBE_ZOMBIE + "Die"
        boomdie_name = c.BOOMDIE

        frame_list = [
            self.helmet_walk_frames,
            self.helmet_swim_frames,
            self.helmet_attack_frames,
            self.walk_frames,
            self.swim_frames,
            self.attack_frames,
            self.losthead_walk_frames,
            self.losthead_attack_frames,
            self.die_frames,
            self.boomdie_frames,
        ]
        name_list = [
            helmet_walk_name,
            helmet_swim_name,
            helmet_attack_name,
            walk_name,
            swim_name,
            attack_name,
            losthead_walk_name,
            losthead_attack_name,
            die_name,
            boomdie_name,
        ]

        for i, name in enumerate(name_list):
            self.loadFrames(frame_list[i], name)

        self.frames = self.helmet_walk_frames


class BucketHeadDuckyTubeZombie(Zombie):
    def __init__(self, x, y, head_group):
        Zombie.__init__(
            self,
            x,
            y,
            c.BUCKETHEAD_DUCKY_TUBE_ZOMBIE,
            head_group,
            helmet_health=c.BUCKETHEAD_HEALTH,
            can_swim=True,
        )

    def loadImages(self):
        self.helmet_walk_frames = []
        self.walk_frames = []
        self.helmet_swim_frames = []
        self.swim_frames = []
        self.helmet_attack_frames = []
        self.attack_frames = []
        self.losthead_walk_frames = []
        self.losthead_attack_frames = []
        self.die_frames = []
        self.boomdie_frames = []

        helmet_walk_name = self.name
        helmet_swim_name = self.name + "Swim"
        helmet_attack_name = self.name + "Attack"
        walk_name = c.DUCKY_TUBE_ZOMBIE
        swim_name = c.DUCKY_TUBE_ZOMBIE + "Swim"
        attack_name = c.DUCKY_TUBE_ZOMBIE + "Attack"
        losthead_walk_name = c.DUCKY_TUBE_ZOMBIE + "LostHead"
        losthead_attack_name = c.DUCKY_TUBE_ZOMBIE + "LostHead"
        die_name = c.DUCKY_TUBE_ZOMBIE + "Die"
        boomdie_name = c.BOOMDIE

        frame_list = [
            self.helmet_walk_frames,
            self.helmet_swim_frames,
            self.helmet_attack_frames,
            self.walk_frames,
            self.swim_frames,
            self.attack_frames,
            self.losthead_walk_frames,
            self.losthead_attack_frames,
            self.die_frames,
            self.boomdie_frames,
        ]
        name_list = [
            helmet_walk_name,
            helmet_swim_name,
            helmet_attack_name,
            walk_name,
            swim_name,
            attack_name,
            losthead_walk_name,
            losthead_attack_name,
            die_name,
            boomdie_name,
        ]

        for i, name in enumerate(name_list):
            self.loadFrames(frame_list[i], name)

        self.frames = self.helmet_walk_frames


class PoleVaultingZombie(Zombie):
    def __init__(self, x, y, head_group):
        Zombie.__init__(
            self,
            x,
            y,
            c.POLE_VAULTING_ZOMBIE,
            head_group=head_group,
            body_health=c.POLE_VAULTING_HEALTH,
            losthead_health=c.POLE_VAULTING_LOSTHEAD_HEALTH,
        )
        self.speed = 1.88
        self.jumped = False
        self.jumping = False

    def loadImages(self):
        self.walk_frames = []
        self.attack_frames = []
        self.losthead_walk_frames = []
        self.losthead_attack_frames = []
        self.die_frames = []
        self.boomdie_frames = []
        self.walk_before_jump_frames = []
        self.jump_frames = []

        walk_name = self.name + "WalkAfterJump"
        attack_name = self.name + "Attack"
        losthead_walk_name = self.name + "LostHead"
        losthead_attack_name = self.name + "LostHeadAttack"
        die_name = self.name + "Die"
        boomdie_name = c.BOOMDIE
        walk_before_jump_name = self.name
        jump_name = self.name + "Jump"

        frame_list = [
            self.walk_frames,
            self.attack_frames,
            self.losthead_walk_frames,
            self.losthead_attack_frames,
            self.die_frames,
            self.boomdie_frames,
            self.walk_before_jump_frames,
            self.jump_frames,
        ]
        name_list = [
            walk_name,
            attack_name,
            losthead_walk_name,
            losthead_attack_name,
            die_name,
            boomdie_name,
            walk_before_jump_name,
            jump_name,
        ]

        for i, name in enumerate(name_list):
            self.loadFrames(frame_list[i], name)

        self.frames = self.walk_before_jump_frames

    def setJump(self, successfullyJumped, jump_x):
        if not self.jumping:
            self.jumping = True
            self.changeFrames(self.jump_frames)
            self.successfullyJumped = successfullyJumped
            self.jump_x = jump_x
            # 播放跳跃音效
            c.SOUND_POLEVAULT_JUMP.play()

    def animation(self):
        if self.state == c.FREEZE:
            self.image.set_alpha(192)
            return

        if (self.current_time - self.animate_timer) > (self.animate_interval * self.getTimeRatio()):
            self.frame_index += 1
            if self.state == c.WALK:
                if self.jumping and (not self.jumped):
                    if self.successfullyJumped:
                        self.rect.x -= 5
                    else:
                        self.rect.x -= 1
            if self.frame_index >= self.frame_num:
                if self.state == c.DIE:
                    self.kill()
                    return
                self.frame_index = 0
                if self.jumping and (not self.jumped):
                    self.changeFrames(self.walk_frames)
                    if self.successfullyJumped:
                        self.rect.centerx = self.jump_x
                    self.jumped = True
                    self.speed = 1.04
            self.animate_timer = self.current_time

        self.image = self.frames[self.frame_index]
        if self.is_hypno:
            self.image = pg.transform.flip(self.image, True, False)
        self.mask = pg.mask.from_surface(self.image)
        if (self.current_time - self.hit_timer) >= 200:
            self.image.set_alpha(255)
        else:
            self.image.set_alpha(192)

    def setWalk(self):
        self.state = c.WALK
        self.animate_interval = self.walk_animate_interval
        if self.jumped:
            self.changeFrames(self.walk_frames)

    def setFreeze(self, ice_trap_image):
        # 起跳但是没有落地时不设置冰冻
        if self.jumping and (not self.jumped):
            self.ice_slow_timer = self.current_time
            self.ice_slow_ratio = 2
        else:
            self.freeze_timer = self.current_time
            self.old_state = self.state
            self.state = c.FREEZE
            self.ice_trap_image = ice_trap_image
            self.ice_trap_rect = ice_trap_image.get_rect()
            self.ice_trap_rect.centerx = self.rect.centerx
            self.ice_trap_rect.bottom = self.rect.bottom


class Zomboni(Zombie):
    def __init__(self, x, y, plant_group, map, IceFrozenPlot):
        Zombie.__init__(self, x, y, c.ZOMBONI, body_health=c.ZOMBONI_HEALTH)
        self.plant_group = plant_group
        self.map = map
        self.IceFrozenPlot = IceFrozenPlot
        self.die_animate_interval = 70
        self.boomDie_animate_interval = 150
        # 播放冰车生成音效
        c.SOUND_ZOMBONI.play()

    def loadImages(self):
        self.walk_frames = []
        self.walk_damaged1_frames = []
        self.walk_damaged2_frames = []
        self.losthead_walk_frames = []
        self.die_frames = []
        self.boomdie_frames = []

        walk_name = self.name
        walk_damaged1_name = self.name + "Damaged1"
        walk_damaged2_name = self.name + "Damaged2"
        losthead_walk_name = self.name + "Damaged2"
        die_name = self.name + "Die"
        boomdie_name = self.name + "BoomDie"

        frame_list = [
            self.walk_frames,
            self.walk_damaged1_frames,
            self.walk_damaged2_frames,
            self.losthead_walk_frames,
            self.die_frames,
            self.boomdie_frames,
        ]
        name_list = [
            walk_name,
            walk_damaged1_name,
            walk_damaged2_name,
            losthead_walk_name,
            die_name,
            boomdie_name,
        ]

        for i, name in enumerate(name_list):
            self.loadFrames(frame_list[i], name)

        self.frames = self.walk_frames

    def updateIceSlow(self):
        # 冰车僵尸不可冰冻
        self.ice_slow_ratio = 1

    def setFreeze(self, ice_trap_image):
        pass

    def walking(self):
        if self.checkToDie(self.losthead_walk_frames):
            return

        if self.health <= c.ZOMBONI_DAMAGED2_HEALTH:
            self.changeFrames(self.walk_damaged2_frames)
        elif self.health <= c.ZOMBONI_DAMAGED1_HEALTH:
            self.changeFrames(self.walk_damaged1_frames)

        if (self.current_time - self.walk_timer) > (
            c.ZOMBIE_WALK_INTERVAL * self.getTimeRatio()
        ) and (not self.losthead):
            self.walk_timer = self.current_time
            if self.is_hypno:
                self.rect.x += 1
            else:
                self.rect.x -= 1

            # 行进时碾压
            for plant in self.plant_group:
                # 地刺和地刺王不用检验
                if (plant.name not in {c.SPIKEWEED}) and (
                    self.rect.centerx <= plant.rect.right <= self.rect.right
                ):
                    # 扣除生命值为可能的最大有限生命值
                    plant.health -= 8000

            # 造冰
            map_x, map_y = self.map.getMapIndex(self.rect.right - 40, self.rect.bottom)
            if 0 <= map_x < c.GRID_X_LEN:
                if c.ICEFROZENPLOT not in self.map.map[map_y][map_x]:
                    x, y = self.map.getMapGridPos(map_x, map_y)
                    self.plant_group.add(self.IceFrozenPlot(x, y))
                    self.map.map[map_y][map_x][c.MAP_PLANT].add(c.ICEFROZENPLOT)

            self.speed = max(0.6, 1.5 - (c.GRID_X_LEN + 1 - map_x) * 0.225)

    def setDie(self):
        self.state = c.DIE
        self.animate_interval = self.die_animate_interval
        self.changeFrames(self.die_frames)
        # 播放冰车爆炸音效
        c.SOUND_ZOMBONI_EXPLOSION.play()


class SnorkelZombie(Zombie):
    def __init__(self, x, y, head_group):
        Zombie.__init__(self, x, y, c.SNORKELZOMBIE, can_swim=True)
        self.speed = 1.6
        self.walk_animate_interval = 50
        self.canSetAttack = True

    def loadImages(self):
        self.walk_frames = []
        self.swim_frames = []
        self.attack_frames = []
        self.jump_frames = []
        self.float_frames = []
        self.sink_frames = []
        self.losthead_walk_frames = []
        self.losthead_attack_frames = []
        self.die_frames = []
        self.boomdie_frames = []

        walk_name = self.name
        swim_name = self.name + "Dive"
        attack_name = self.name + "Attack"
        jump_name = self.name + "Jump"
        float_name = self.name + "Float"
        sink_name = self.name + "Sink"
        losthead_walk_name = self.name + "LostHead"
        losthead_attack_name = self.name + "LostHeadAttack"
        die_name = self.name + "Die"
        boomdie_name = c.BOOMDIE

        frame_list = [
            self.walk_frames,
            self.swim_frames,
            self.attack_frames,
            self.jump_frames,
            self.float_frames,
            self.sink_frames,
            self.losthead_walk_frames,
            self.losthead_attack_frames,
            self.die_frames,
            self.boomdie_frames,
        ]
        name_list = [
            walk_name,
            swim_name,
            attack_name,
            jump_name,
            float_name,
            sink_name,
            losthead_walk_name,
            losthead_attack_name,
            die_name,
            boomdie_name,
        ]

        for i, name in enumerate(name_list):
            self.loadFrames(frame_list[i], name)

        self.frames = self.walk_frames

    def walking(self):
        if self.checkToDie(self.losthead_walk_frames):
            return

        # 在水池范围内
        # 在右侧岸左
        if self.rect.centerx <= c.MAP_POOL_FRONT_X - 25:
            # 在左侧岸右，左侧岸位置为预估
            if self.rect.right - 25 >= c.MAP_POOL_OFFSET_X:
                # 还未进入游泳状态
                if not self.swimming:
                    self.swimming = True
                    self.changeFrames(self.jump_frames)
                    self.speed = 1.175
                    # 播放入水音效
                    c.SOUND_ZOMBIE_ENTERING_WATER.play()
            # 已经接近家门口并且上岸
            else:
                if self.swimming:
                    self.changeFrames(self.walk_frames)
                    self.speed = 1.6
                    self.swimming = False
        # 被魅惑时走到岸上需要起立
        elif self.is_hypno and (self.rect.right > c.MAP_POOL_FRONT_X + 55):  # 常数拟合暂时缺乏检验
            if self.swimming:
                self.speed = 1.6
                self.changeFrames(self.walk_frames)
            self.swimming = False
        if (self.current_time - self.walk_timer) > (c.ZOMBIE_WALK_INTERVAL * self.getTimeRatio()):
            self.handleGarlicYChange()
            self.walk_timer = self.current_time
            # 正在上浮或者下潜不用移动
            if (self.frames == self.float_frames) or (self.frames == self.sink_frames):
                pass
            elif self.is_hypno:
                self.rect.x += 1
            else:
                self.rect.x -= 1

    def animation(self):
        if self.state == c.FREEZE:
            self.image.set_alpha(192)
            return

        if (self.current_time - self.animate_timer) > (self.animate_interval * self.getTimeRatio()):
            self.frame_index += 1
            if self.frame_index >= self.frame_num:
                if self.state == c.DIE:
                    self.kill()
                    return
                elif self.frames == self.jump_frames:
                    self.changeFrames(self.swim_frames)
                elif self.frames == self.sink_frames:
                    self.changeFrames(self.swim_frames)
                    # 还需要改回原来的可进入攻击状态的设定
                    self.canSetAttack = True
                elif self.frames == self.float_frames:
                    self.state = c.ATTACK
                    self.attack_timer = self.current_time
                    self.changeFrames(self.attack_frames)
                self.frame_index = 0
            self.animate_timer = self.current_time

        self.image = self.frames[self.frame_index]
        if self.is_hypno:
            self.image = pg.transform.flip(self.image, True, False)
        self.mask = pg.mask.from_surface(self.image)

        if (self.current_time - self.hit_timer) >= 200:
            self.image.set_alpha(255)
        else:
            self.image.set_alpha(192)

    # 注意潜水僵尸较为特殊：这里的setAttack并没有直接触发攻击状态，而是触发从水面浮起
    def setAttack(self, prey, is_plant=True):
        self.prey = prey  # prey can be plant or other zombies
        self.prey_is_plant = is_plant
        self.animate_interval = self.attack_animate_interval

        if self.losthead:
            self.changeFrames(self.losthead_attack_frames)
        elif self.canSetAttack:
            self.changeFrames(self.float_frames)
            self.canSetAttack = False

    def setWalk(self):
        self.state = c.WALK
        self.animate_interval = self.walk_animate_interval
        self.swimming = True
        self.changeFrames(self.sink_frames)
