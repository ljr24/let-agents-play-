"""Original pypvz entity behavior, grouped by responsibility. See docs/UPSTREAM.md."""
import random
import pygame as pg
from game import constants as c, assets as tool
from game.entities.plants.base import Plant


class Car(pg.sprite.Sprite):
    def __init__(self, x: int, y: int, map_y: int):
        pg.sprite.Sprite.__init__(self)

        rect = tool.GFX[c.CAR].get_rect()
        width, height = rect.w, rect.h
        self.image = tool.get_image(tool.GFX[c.CAR], 0, 0, width, height)
        self.mask = pg.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.bottom = y
        self.map_y = map_y
        self.state = c.IDLE
        self.dead = False

    def update(self, game_info: dict):
        self.current_time = game_info[c.CURRENT_TIME]
        if self.state == c.WALK:
            self.rect.x += 5
        if self.rect.x > c.SCREEN_WIDTH + 25:
            self.dead = True

    def setWalk(self):
        if self.state == c.IDLE:
            self.state = c.WALK
            # 播放音效
            c.SOUND_CAR_WALKING.play()

    def draw(self, surface):
        surface.blit(self.image, self.rect)


class Sun(Plant):
    def __init__(self, x, y, dest_x, dest_y, is_big=True):
        if is_big:
            scale = 0.9
            self.sun_value = c.SUN_VALUE
        else:
            scale = 0.6
            self.sun_value = 15
        Plant.__init__(self, x, y, c.SUN, 0, None, scale)
        self.move_speed = 1
        self.dest_x = dest_x
        self.dest_y = dest_y
        self.die_timer = 0

    def handleState(self):
        if self.rect.centerx != self.dest_x:
            self.rect.centerx += (
                self.move_speed if self.rect.centerx < self.dest_x else -self.move_speed
            )
        if self.rect.bottom != self.dest_y:
            self.rect.bottom += (
                self.move_speed if self.rect.bottom < self.dest_y else -self.move_speed
            )

        if self.rect.centerx == self.dest_x and self.rect.bottom == self.dest_y:
            if self.die_timer == 0:
                self.die_timer = self.current_time
            elif (self.current_time - self.die_timer) > c.SUN_LIVE_TIME:
                self.state = c.DIE
                self.kill()

    def checkCollision(self, x, y):
        if self.state == c.DIE:
            return False
        if x >= self.rect.x and x <= self.rect.right and y >= self.rect.y and y <= self.rect.bottom:
            self.state = c.DIE
            self.kill()
            return True
        return False


class Hole(Plant):
    def __init__(self, x, y, plot_type):
        # 指定区域类型这一句必须放在前面，否则加载图片判断将会失败
        self.plot_type = plot_type
        Plant.__init__(self, x, y, c.HOLE, c.INF, None)
        self.timer = 0
        self.shallow = False
        self.attack_check = c.CHECK_ATTACK_NEVER

    def loadImages(self, name, scale):
        self.idle_frames = []
        self.idle2_frames = []
        self.water_frames = []
        self.water2_frames = []
        self.roof_frames = []
        self.roof2_frames = []

        idle_name = name
        idle2_name = name + "Shallow"
        water_name = name + "Water"
        water2_name = name + "WaterShallow"
        roof_name = name + "Roof"
        roof2_name = name + "RoofShallow"

        frame_list = [
            self.idle_frames,
            self.idle2_frames,
            self.water_frames,
            self.water2_frames,
            self.roof_frames,
            self.roof2_frames,
        ]
        name_list = [
            idle_name,
            idle2_name,
            water_name,
            water2_name,
            roof_name,
            roof2_name,
        ]

        for i, name in enumerate(name_list):
            self.loadFrames(frame_list[i], name)

        if self.plot_type == c.MAP_TILE:
            self.frames = self.roof_frames
        elif self.plot_type == c.MAP_WATER:
            self.frames = self.water_frames
        else:
            self.frames = self.idle_frames

    def idling(self):
        if self.timer == 0:
            self.timer = self.current_time
        elif (not self.shallow) and (self.current_time - self.timer >= 90000):
            if self.plot_type == c.MAP_TILE:
                self.frames = self.roof2_frames
            elif self.plot_type == c.MAP_WATER:
                self.frames = self.water2_frames
            else:
                self.frames = self.idle2_frames
            self.shallow = True
        elif self.current_time - self.timer >= 180000:
            self.health = 0


class Grave(Plant):
    def __init__(self, x, y):
        Plant.__init__(self, x, y, c.GRAVE, c.INF, None)
        self.frame_index = random.randint(0, self.frame_num - 1)
        self.image = self.frames[self.frame_index]
        self.mask = pg.mask.from_surface(self.image)
        self.attack_check = c.CHECK_ATTACK_NEVER

    def animation(self):
        pass


class IceFrozenPlot(Plant):
    def __init__(self, x, y):
        Plant.__init__(self, x, y, c.ICEFROZENPLOT, c.INF, None)
        self.timer = 0
        self.attack_check = c.CHECK_ATTACK_NEVER

    def idling(self):
        if self.timer == 0:
            self.timer = self.current_time
        elif self.current_time - self.timer >= 30000:
            self.health = 0
