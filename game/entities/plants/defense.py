"""Original pypvz entity behavior, grouped by responsibility. See docs/UPSTREAM.md."""
import random
import pygame as pg
from game import constants as c, assets as tool
from game.entities.plants.base import Plant


class WallNut(Plant):
    def __init__(self, x, y):
        Plant.__init__(self, x, y, c.WALLNUT, c.WALLNUT_HEALTH, None)
        self.load_images()
        self.cracked1 = False
        self.cracked2 = False
        self.attack_check = c.CHECK_ATTACK_NEVER

    def load_images(self):
        self.cracked1_frames = []
        self.cracked2_frames = []

        cracked1_frames_name = self.name + "_cracked1"
        cracked2_frames_name = self.name + "_cracked2"

        self.loadFrames(self.cracked1_frames, cracked1_frames_name)
        self.loadFrames(self.cracked2_frames, cracked2_frames_name)

    def idling(self):
        if (not self.cracked1) and self.health <= c.WALLNUT_CRACKED1_HEALTH:
            self.changeFrames(self.cracked1_frames)
            self.cracked1 = True
        elif (not self.cracked2) and self.health <= c.WALLNUT_CRACKED2_HEALTH:
            self.changeFrames(self.cracked2_frames)
            self.cracked2 = True


class TallNut(Plant):
    def __init__(self, x, y):
        Plant.__init__(self, x, y, c.TALLNUT, c.TALLNUT_HEALTH, None)
        self.load_images()
        self.cracked1 = False
        self.cracked2 = False
        self.attack_check = c.CHECK_ATTACK_NEVER

    def load_images(self):
        self.cracked1_frames = []
        self.cracked2_frames = []

        cracked1_frames_name = self.name + "_cracked1"
        cracked2_frames_name = self.name + "_cracked2"

        self.loadFrames(self.cracked1_frames, cracked1_frames_name)
        self.loadFrames(self.cracked2_frames, cracked2_frames_name)

    def idling(self):
        if not self.cracked1 and self.health <= c.TALLNUT_CRACKED1_HEALTH:
            self.changeFrames(self.cracked1_frames)
            self.cracked1 = True
        elif not self.cracked2 and self.health <= c.TALLNUT_CRACKED2_HEALTH:
            self.changeFrames(self.cracked2_frames)
            self.cracked2 = True


class PumpkinHead(Plant):
    def __init__(self, x, y):
        Plant.__init__(self, x, y, c.PUMPKINHEAD, c.WALLNUT_HEALTH, None)
        self.load_images()
        self.cracked1 = False
        self.cracked2 = False
        self.animate_interval = 160
        self.attack_check = c.CHECK_ATTACK_NEVER

    def load_images(self):
        self.cracked1_frames = []
        self.cracked2_frames = []

        cracked1_frames_name = self.name + "_cracked1"
        cracked2_frames_name = self.name + "_cracked2"

        self.loadFrames(self.cracked1_frames, cracked1_frames_name)
        self.loadFrames(self.cracked2_frames, cracked2_frames_name)

    def idling(self):
        if not self.cracked1 and self.health <= c.WALLNUT_CRACKED1_HEALTH:
            self.changeFrames(self.cracked1_frames)
            self.cracked1 = True
        elif not self.cracked2 and self.health <= c.WALLNUT_CRACKED2_HEALTH:
            self.changeFrames(self.cracked2_frames)
            self.cracked2 = True


class WallNutBowling(Plant):
    def __init__(self, x, y, map_y, level):
        Plant.__init__(self, x, y, c.WALLNUTBOWLING, 1, None)
        self.map_y = map_y
        self.level = level
        self.init_rect = self.rect.copy()
        self.rotate_degree = 0
        self.animate_interval = 200
        self.move_timer = 0
        self.move_interval = 70
        self.vel_x = random.randint(12, 15)
        self.vel_y = 0
        self.disable_hit_y = -1
        self.attack_check = c.CHECK_ATTACK_NEVER

    def loadImages(self, name, scale):
        self.loadFrames(self.frames, name, 1)

    def idling(self):
        if self.move_timer == 0:
            self.move_timer = self.current_time
        elif (self.current_time - self.move_timer) >= self.move_interval:
            self.rotate_degree = (self.rotate_degree - 30) % 360
            self.init_rect.x += self.vel_x
            self.init_rect.y += self.vel_y
            self.handleMapYPosition()
            if self.shouldChangeDirection():
                self.changeDirection(-1)
            if self.init_rect.x > c.SCREEN_WIDTH + 25:
                self.health = 0
            self.move_timer += self.move_interval

    def canHit(self, map_y):
        if self.disable_hit_y == map_y:
            return False
        return True

    def handleMapYPosition(self):
        map_y1 = self.level.map.getMapIndex(self.init_rect.x, self.init_rect.centery)[1]
        map_y2 = self.level.map.getMapIndex(self.init_rect.x, self.init_rect.bottom)[1]
        if self.map_y != map_y1 and map_y1 == map_y2:
            # wallnut bowls to another row, should modify which plant group it belongs to
            self.level.plant_groups[self.map_y].remove(self)
            self.level.plant_groups[map_y1].add(self)
            self.map_y = map_y1

    def shouldChangeDirection(self):
        if self.init_rect.centery <= c.MAP_OFFSET_Y:
            return True
        elif self.init_rect.bottom + 20 >= c.SCREEN_HEIGHT:
            return True
        return False

    def changeDirection(self, map_y):
        if self.vel_y == 0:
            if self.map_y == 0:
                self.vel_y = self.vel_x
            elif self.map_y == (c.GRID_Y_LEN - 1):  # 坚果保龄球显然没有泳池的6行情形
                self.vel_y = -self.vel_x
            else:
                if random.randint(0, 1):
                    self.vel_y = self.vel_x
                else:
                    self.vel_y = -self.vel_x
        else:
            self.vel_y = -self.vel_y

        self.disable_hit_y = map_y

    def animation(self):
        image = self.frames[self.frame_index]
        self.image = pg.transform.rotate(image, self.rotate_degree)
        self.mask = pg.mask.from_surface(self.image)
        # must keep the center postion of image when rotate
        self.rect = self.image.get_rect(center=self.init_rect.center)


class RedWallNutBowling(Plant):
    def __init__(self, x, y):
        Plant.__init__(self, x, y, c.REDWALLNUTBOWLING, 1, None)
        self.orig_y = y
        self.explode_timer = 0
        self.explode_y_range = 1
        self.explode_x_range = c.GRID_X_SIZE * 1.5
        self.init_rect = self.rect.copy()
        self.rotate_degree = 0
        self.animate_interval = 200
        self.move_timer = 0
        self.move_interval = 70
        self.vel_x = random.randint(12, 15)
        self.start_boom = False
        self.boomed = False

    def loadImages(self, name, scale):
        self.idle_frames = []
        self.loadFrames(self.idle_frames, name, 1)

        frame = tool.GFX[c.BOOM_IMAGE]
        rect = frame.get_rect()
        image = tool.get_image(frame, 0, 0, rect.w, rect.h)
        self.explode_frames = (image,)

        self.frames = self.idle_frames

    def idling(self):
        if self.move_timer == 0:
            self.move_timer = self.current_time
        elif (self.current_time - self.move_timer) >= self.move_interval:
            self.rotate_degree = (self.rotate_degree - 30) % 360
            self.init_rect.x += self.vel_x
            if self.init_rect.x > c.SCREEN_WIDTH + 25:
                self.health = 0
            self.move_timer += self.move_interval

    def attacking(self):
        if self.explode_timer == 0:
            self.start_boom = True
            self.explode_timer = self.current_time
            self.changeFrames(self.explode_frames)
            # 播放爆炸音效
            c.SOUND_BOMB.play()
        elif (self.current_time - self.explode_timer) > 500:
            self.health = 0

    def animation(self):
        if (self.current_time - self.animate_timer) > self.animate_interval:
            self.frame_index += 1
            if self.frame_index >= self.frame_num:
                self.frame_index = 0
            self.animate_timer = self.current_time

        image = self.frames[self.frame_index]
        if self.state == c.IDLE:
            self.image = pg.transform.rotate(image, self.rotate_degree)
        else:
            self.image = image
        self.mask = pg.mask.from_surface(self.image)
        # must keep the center postion of image when rotate
        self.rect = self.image.get_rect(center=self.init_rect.center)

    def getPosition(self):
        return (self.rect.centerx, self.orig_y)


class GiantWallNut(Plant):
    def __init__(self, x, y):
        Plant.__init__(self, x, y, c.GIANTWALLNUT, 1, None)
        self.init_rect = self.rect.copy()
        self.rotate_degree = 0
        self.animate_interval = 200
        self.move_timer = 0
        self.move_interval = 70
        self.vel_x = random.randint(15, 18)
        self.attack_check = c.CHECK_ATTACK_NEVER

    def idling(self):
        if self.move_timer == 0:
            self.move_timer = self.current_time
        elif (self.current_time - self.move_timer) >= self.move_interval:
            self.rotate_degree = (self.rotate_degree - 30) % 360
            self.init_rect.x += self.vel_x
            if self.init_rect.x > c.SCREEN_WIDTH:
                self.health = 0
            self.move_timer += self.move_interval

    def animation(self):
        image = self.frames[self.frame_index]
        self.image = pg.transform.rotate(image, self.rotate_degree)
        self.mask = pg.mask.from_surface(self.image)
        # must keep the center postion of image when rotate
        self.rect = self.image.get_rect(center=self.init_rect.center)
