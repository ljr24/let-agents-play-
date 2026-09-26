"""Original pypvz entity behavior, grouped by responsibility. See docs/UPSTREAM.md."""
import pygame as pg
from game import constants as c, assets as tool
from game.entities.plants.base import Plant


class CherryBomb(Plant):
    def __init__(self, x, y):
        Plant.__init__(self, x, y, c.CHERRYBOMB, c.INF, None)
        self.state = c.ATTACK
        self.start_boom = False
        self.boomed = False
        self.bomb_timer = 0
        self.explode_y_range = 1
        self.explode_x_range = c.GRID_X_SIZE * 1.5

    def setBoom(self):
        frame = tool.GFX[c.BOOM_IMAGE]
        rect = frame.get_rect()
        width, height = rect.w, rect.h

        old_rect = self.rect
        image = tool.get_image(frame, 0, 0, width, height, c.BLACK, 1)
        self.image = image
        self.mask = pg.mask.from_surface(self.image)
        self.rect = image.get_rect()
        self.rect.centerx = old_rect.centerx
        self.rect.centery = old_rect.centery
        self.start_boom = True

    def animation(self):
        if self.start_boom:
            if self.bomb_timer == 0:
                self.bomb_timer = self.current_time
                # 播放爆炸音效
                c.SOUND_BOMB.play()
            elif (self.current_time - self.bomb_timer) > 500:
                self.health = 0
        else:
            if (self.current_time - self.animate_timer) > 100:
                self.frame_index += 1
                if self.frame_index >= self.frame_num:
                    self.setBoom()
                    return
                self.animate_timer = self.current_time

            self.image = self.frames[self.frame_index]
            self.mask = pg.mask.from_surface(self.image)

        if self.current_time - self.highlight_time < 100:
            self.image.set_alpha(150)
        elif (self.current_time - self.hit_timer) < 200:
            self.image.set_alpha(192)
        else:
            self.image.set_alpha(255)


class PotatoMine(Plant):
    def __init__(self, x, y):
        Plant.__init__(self, x, y, c.POTATOMINE, c.PLANT_HEALTH, None)
        self.animate_interval = 300
        self.is_init = True
        self.init_timer = 0
        self.bomb_timer = 0
        self.explode_x_range = c.GRID_X_SIZE / 2
        self.start_boom = False
        self.boomed = False

    def loadImages(self, name, scale):
        self.init_frames = []
        self.idle_frames = []
        self.explode_frames = []

        init_name = name + "Init"
        idle_name = name
        explode_name = name + "Explode"

        frame_list = [self.init_frames, self.idle_frames, self.explode_frames]
        name_list = [init_name, idle_name, explode_name]

        for i, name in enumerate(name_list):
            self.loadFrames(frame_list[i], name)

        self.frames = self.init_frames

    def idling(self):
        if self.is_init:
            if self.init_timer == 0:
                self.init_timer = self.current_time
            elif (self.current_time - self.init_timer) > 15000:
                self.changeFrames(self.idle_frames)
                self.is_init = False

    def canAttack(self, zombie):  # 土豆雷不可能遇上潜水僵尸
        if zombie.name == c.POLE_VAULTING_ZOMBIE and (not zombie.jumped):
            return False
        # 这里碰撞应当比碰撞一般更容易，就设置成圆形或矩形模式，不宜采用mask
        elif (
            pg.sprite.collide_circle_ratio(0.7)(zombie, self)
            and (not self.is_init)
            and (not zombie.losthead)
        ):
            return True
        return False

    def attacking(self):
        if self.bomb_timer == 0:
            self.bomb_timer = self.current_time
            # 播放音效
            c.SOUND_POTATOMINE.play()
            self.changeFrames(self.explode_frames)
            self.start_boom = True
        elif (self.current_time - self.bomb_timer) > 500:
            self.health = 0


class Jalapeno(Plant):
    def __init__(self, x, y):
        Plant.__init__(self, x, y, c.JALAPENO, c.INF, None)
        self.orig_pos = (x, y)
        self.state = c.ATTACK
        self.start_boom = False
        self.boomed = False
        self.explode_y_range = 0
        self.explode_x_range = 500

    def loadImages(self, name, scale):
        self.explode_frames = []
        explode_name = name + "Explode"
        self.loadFrames(self.explode_frames, explode_name)

        self.loadFrames(self.frames, name)

    def setExplode(self):
        self.changeFrames(self.explode_frames)
        self.animate_timer = self.current_time
        self.rect.x = c.MAP_OFFSET_X
        self.start_boom = True

    def animation(self):
        if self.start_boom:
            if (self.current_time - self.animate_timer) > 100:
                if self.frame_index == 1:
                    # 播放爆炸音效
                    c.SOUND_BOMB.play()
                self.frame_index += 1
                if self.frame_index >= self.frame_num:
                    self.health = 0
                    return
                self.animate_timer = self.current_time
        else:
            if (self.current_time - self.animate_timer) > 100:
                self.frame_index += 1
                if self.frame_index >= self.frame_num:
                    self.setExplode()
                    return
                self.animate_timer = self.current_time
        self.image = self.frames[self.frame_index]
        self.mask = pg.mask.from_surface(self.image)

        if self.current_time - self.highlight_time < 100:
            self.image.set_alpha(150)
        elif (self.current_time - self.hit_timer) < 200:
            self.image.set_alpha(192)
        else:
            self.image.set_alpha(255)

    def getPosition(self):
        return self.orig_pos


class IceShroom(Plant):
    def __init__(self, x, y):
        Plant.__init__(self, x, y, c.ICESHROOM, c.PLANT_HEALTH, None)
        self.orig_pos = (x, y)
        self.start_boom = False
        self.boomed = False

    def loadImages(self, name, scale):
        self.idle_frames = []
        self.snow_frames = []
        self.sleep_frames = []
        self.trap_frames = []

        idle_name = name
        snow_name = name + "Snow"
        sleep_name = name + "Sleep"
        trap_name = name + "Trap"

        frame_list = [
            self.idle_frames,
            self.snow_frames,
            self.sleep_frames,
            self.trap_frames,
        ]
        name_list = [idle_name, snow_name, sleep_name, trap_name]
        scale_list = [1, 1.5, 1, 1]

        for i, name in enumerate(name_list):
            self.loadFrames(frame_list[i], name, scale_list[i])

        self.frames = self.idle_frames

    def setFreeze(self):
        self.changeFrames(self.snow_frames)
        self.animate_timer = self.current_time
        self.rect.x = c.MAP_OFFSET_X
        self.rect.y = c.MAP_OFFSET_Y
        self.start_boom = True

    def animation(self):
        if self.start_boom:
            if (self.current_time - self.animate_timer) > 500:
                self.frame_index += 1
                if self.frame_index >= self.frame_num:
                    self.health = 0
                    return
                self.animate_timer = self.current_time
        else:
            if self.state != c.SLEEP:
                self.health = c.INF
            if (self.current_time - self.animate_timer) > 100:
                self.frame_index += 1
                if self.frame_index >= self.frame_num:
                    if self.state == c.SLEEP:
                        self.frame_index = 0
                    else:
                        self.setFreeze()
                        return
                self.animate_timer = self.current_time
        self.image = self.frames[self.frame_index]
        self.mask = pg.mask.from_surface(self.image)

        if self.current_time - self.highlight_time < 100:
            self.image.set_alpha(150)
        elif (self.current_time - self.hit_timer) < 200:
            self.image.set_alpha(192)
        else:
            self.image.set_alpha(255)

    def getPosition(self):
        return self.orig_pos


class DoomShroom(Plant):
    def __init__(self, x, y, map_plant_set, explode_y_range):
        Plant.__init__(self, x, y, c.DOOMSHROOM, c.PLANT_HEALTH, None)
        self.map_plant_set = map_plant_set
        self.bomb_timer = 0
        self.explode_y_range = explode_y_range
        self.explode_x_range = 250
        self.start_boom = False
        self.boomed = False
        self.original_x = x
        self.original_y = y

    def loadImages(self, name, scale):
        self.idle_frames = []
        self.sleep_frames = []
        self.boom_frames = []

        idle_name = name
        sleep_name = name + "Sleep"
        boom_name = name + "Boom"

        frame_list = [self.idle_frames, self.sleep_frames, self.boom_frames]
        name_list = [idle_name, sleep_name, boom_name]

        for i, name in enumerate(name_list):
            self.loadFrames(frame_list[i], name)

        self.frames = self.idle_frames

    def setBoom(self):
        self.changeFrames(self.boom_frames)
        self.start_boom = True

    def animation(self):
        # 发生了爆炸
        if self.start_boom:
            if self.frame_index == 1:
                self.rect.x -= 80
                self.rect.y += 30
                # 播放爆炸音效
                c.SOUND_DOOMSHROOM.play()
            if (self.current_time - self.animate_timer) > self.animate_interval:
                self.frame_index += 1
            if self.frame_index >= self.frame_num:
                self.health = 0
                self.frame_index = self.frame_num - 1
                self.map_plant_set.add(c.HOLE)
        # 睡觉状态
        elif self.state == c.SLEEP:
            if (self.current_time - self.animate_timer) > self.animate_interval:
                self.frame_index += 1
                if self.frame_index >= self.frame_num:
                    self.frame_index = 0
                self.animate_timer = self.current_time
        # 正常状态
        else:
            self.health = c.INF
            if (self.current_time - self.animate_timer) > 100:
                self.frame_index += 1
                if self.frame_index >= self.frame_num:
                    self.setBoom()
                    return
                self.animate_timer = self.current_time
        self.image = self.frames[self.frame_index]
        self.mask = pg.mask.from_surface(self.image)

        if self.current_time - self.highlight_time < 100:
            self.image.set_alpha(150)
        elif (self.current_time - self.hit_timer) < 200:
            self.image.set_alpha(192)
        else:
            self.image.set_alpha(255)
