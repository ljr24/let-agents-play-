"""Original pypvz entity behavior, grouped by responsibility. See docs/UPSTREAM.md."""
from game import constants as c
from game.entities.plants.base import Plant
from game.entities.props import Sun


class SunFlower(Plant):
    def __init__(self, x, y, sun_group):
        Plant.__init__(self, x, y, c.SUNFLOWER, c.PLANT_HEALTH, None)
        self.sun_timer = 0
        self.sun_group = sun_group
        self.attack_check = c.CHECK_ATTACK_NEVER

    def idling(self):
        if self.sun_timer == 0:
            self.sun_timer = self.current_time - (c.FLOWER_SUN_INTERVAL - 6000)
        elif (self.current_time - self.sun_timer) > c.FLOWER_SUN_INTERVAL:
            self.sun_group.add(
                Sun(
                    self.rect.centerx,
                    self.rect.bottom,
                    self.rect.right,
                    self.rect.bottom + self.rect.h // 2,
                )
            )
            self.sun_timer = self.current_time


class SunShroom(Plant):
    def __init__(self, x, y, sun_group):
        Plant.__init__(self, x, y, c.SUNSHROOM, c.PLANT_HEALTH, None)
        self.animate_interval = 140
        self.sun_timer = 0
        self.sun_group = sun_group
        self.is_big = False
        self.change_timer = 0

    def loadImages(self, name, scale):
        self.idle_frames = []
        self.big_frames = []
        self.sleep_frames = []

        idle_name = name
        big_name = name + "Big"
        sleep_name = name + "Sleep"

        frame_list = [self.idle_frames, self.big_frames, self.sleep_frames]
        name_list = [idle_name, big_name, sleep_name]

        for i, name in enumerate(name_list):
            self.loadFrames(frame_list[i], name)

        self.frames = self.idle_frames

    def idling(self):
        if not self.is_big:
            if self.change_timer == 0:
                self.change_timer = self.current_time
            elif (self.current_time - self.change_timer) > 100000:
                self.changeFrames(self.big_frames)
                self.is_big = True
                # 播放长大音效
                c.SOUND_PLANT_GROW.play()
        if self.sun_timer == 0:
            self.sun_timer = self.current_time - (c.FLOWER_SUN_INTERVAL - 6000)
        elif (self.current_time - self.sun_timer) > c.FLOWER_SUN_INTERVAL:
            self.sun_group.add(
                Sun(
                    self.rect.centerx,
                    self.rect.bottom,
                    self.rect.right,
                    self.rect.bottom + self.rect.h // 2,
                    self.is_big,
                )
            )
            self.sun_timer = self.current_time
