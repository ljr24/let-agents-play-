"""Original pypvz entity behavior, grouped by responsibility. See docs/UPSTREAM.md."""
import pygame as pg
from game import constants as c, assets as tool


class Plant(pg.sprite.Sprite):
    def __init__(self, x, y, name, health, bullet_group, scale=1):
        pg.sprite.Sprite.__init__(self)

        self.frames = []
        self.frame_index = 0
        self.loadImages(name, scale)
        self.frame_num = len(self.frames)
        self.image = self.frames[self.frame_index]
        self.mask = pg.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.rect.centerx = x
        self.rect.bottom = y

        self.name = name
        self.health = health
        self.state = c.IDLE
        self.bullet_group = bullet_group
        self.animate_timer = 0
        self.animate_interval = 70  # 帧播放间隔
        self.hit_timer = 0
        # 被铲子指向时间
        self.highlight_time = 0

        self.attack_check = c.CHECK_ATTACK_ALWAYS

    def loadFrames(self, frames, name, scale=1, color=c.BLACK):
        frame_list = tool.GFX[name]
        if name in c.PLANT_RECT:
            data = c.PLANT_RECT[name]
            x, y, width, height = (
                data["x"],
                data["y"],
                data["width"],
                data["height"],
            )
        else:
            x, y = 0, 0
            rect = frame_list[0].get_rect()
            width, height = rect.w, rect.h

        for frame in frame_list:
            frames.append(tool.get_image(frame, x, y, width, height, color, scale))

    def loadImages(self, name, scale):
        self.loadFrames(self.frames, name, scale)

    def changeFrames(self, frames):
        # change image frames and modify rect position
        self.frames = frames
        self.frame_num = len(self.frames)
        self.frame_index = 0

        bottom = self.rect.bottom
        x = self.rect.x
        self.image = self.frames[self.frame_index]
        self.mask = pg.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.rect.bottom = bottom
        self.rect.x = x

    def update(self, game_info):
        self.current_time = game_info[c.CURRENT_TIME]
        self.handleState()
        self.animation()

    def handleState(self):
        if self.state == c.IDLE:
            self.idling()
        elif self.state == c.ATTACK:
            self.attacking()
        elif self.state == c.DIGEST:
            self.digest()

    def idling(self):
        pass

    def attacking(self):
        pass

    def digest(self):
        pass

    def animation(self):
        if (self.current_time - self.animate_timer) > self.animate_interval:
            self.frame_index += 1
            if self.frame_index >= self.frame_num:
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

    def canAttack(self, zombie):
        if (zombie.name == c.SNORKELZOMBIE) and (zombie.frames == zombie.swim_frames):
            return False
        if (
            self.state != c.SLEEP
            and zombie.state != c.DIE
            and self.rect.x <= zombie.rect.right
            and zombie.rect.x <= c.SCREEN_WIDTH - 24
        ):
            return True
        return False

    def setAttack(self):
        self.state = c.ATTACK

    def setIdle(self):
        self.state = c.IDLE
        self.is_attacked = False

    def setSleep(self):
        self.state = c.SLEEP
        self.changeFrames(self.sleep_frames)

    def setDamage(self, damage, zombie):
        if not zombie.losthead:
            self.health -= damage
        self.hit_timer = self.current_time
        if (
            (self.name == c.HYPNOSHROOM)
            and (self.state != c.SLEEP)
            and (zombie.name not in {c.ZOMBONI, "投石车僵尸（未实现）", "加刚特尔（未实现）"})
        ):
            self.zombie_to_hypno = zombie

    def getPosition(self):
        return self.rect.centerx, self.rect.bottom
