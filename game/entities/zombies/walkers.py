"""Original pypvz entity behavior, grouped by responsibility. See docs/UPSTREAM.md."""
import pygame as pg
from game import constants as c
from game.entities.zombies.base import Zombie


class NormalZombie(Zombie):
    def __init__(self, x, y, head_group):
        Zombie.__init__(self, x, y, c.NORMAL_ZOMBIE, head_group)

    def loadImages(self):
        self.walk_frames = []
        self.attack_frames = []
        self.losthead_walk_frames = []
        self.losthead_attack_frames = []
        self.die_frames = []
        self.boomdie_frames = []

        walk_name = self.name
        attack_name = self.name + "Attack"
        losthead_walk_name = self.name + "LostHead"
        losthead_attack_name = self.name + "LostHeadAttack"
        die_name = self.name + "Die"
        boomdie_name = c.BOOMDIE

        frame_list = [
            self.walk_frames,
            self.attack_frames,
            self.losthead_walk_frames,
            self.losthead_attack_frames,
            self.die_frames,
            self.boomdie_frames,
        ]
        name_list = [
            walk_name,
            attack_name,
            losthead_walk_name,
            losthead_attack_name,
            die_name,
            boomdie_name,
        ]

        for i, name in enumerate(name_list):
            self.loadFrames(frame_list[i], name)

        self.frames = self.walk_frames


class ConeHeadZombie(Zombie):
    def __init__(self, x, y, head_group):
        Zombie.__init__(
            self,
            x,
            y,
            c.CONEHEAD_ZOMBIE,
            head_group,
            helmet_health=c.CONEHEAD_HEALTH,
        )

    def loadImages(self):
        self.helmet_walk_frames = []
        self.helmet_attack_frames = []
        self.walk_frames = []
        self.attack_frames = []
        self.losthead_walk_frames = []
        self.losthead_attack_frames = []
        self.die_frames = []
        self.boomdie_frames = []

        helmet_walk_name = self.name
        helmet_attack_name = self.name + "Attack"
        walk_name = c.NORMAL_ZOMBIE
        attack_name = c.NORMAL_ZOMBIE + "Attack"
        losthead_walk_name = c.NORMAL_ZOMBIE + "LostHead"
        losthead_attack_name = c.NORMAL_ZOMBIE + "LostHeadAttack"
        die_name = c.NORMAL_ZOMBIE + "Die"
        boomdie_name = c.BOOMDIE

        frame_list = [
            self.helmet_walk_frames,
            self.helmet_attack_frames,
            self.walk_frames,
            self.attack_frames,
            self.losthead_walk_frames,
            self.losthead_attack_frames,
            self.die_frames,
            self.boomdie_frames,
        ]
        name_list = [
            helmet_walk_name,
            helmet_attack_name,
            walk_name,
            attack_name,
            losthead_walk_name,
            losthead_attack_name,
            die_name,
            boomdie_name,
        ]

        for i, name in enumerate(name_list):
            self.loadFrames(frame_list[i], name)

        self.frames = self.helmet_walk_frames


class BucketHeadZombie(Zombie):
    def __init__(self, x, y, head_group):
        Zombie.__init__(
            self,
            x,
            y,
            c.BUCKETHEAD_ZOMBIE,
            head_group,
            helmet_health=c.BUCKETHEAD_HEALTH,
        )

    def loadImages(self):
        self.helmet_walk_frames = []
        self.helmet_attack_frames = []
        self.walk_frames = []
        self.attack_frames = []
        self.losthead_walk_frames = []
        self.losthead_attack_frames = []
        self.die_frames = []
        self.boomdie_frames = []

        helmet_walk_name = self.name
        helmet_attack_name = self.name + "Attack"
        walk_name = c.NORMAL_ZOMBIE
        attack_name = c.NORMAL_ZOMBIE + "Attack"
        losthead_walk_name = c.NORMAL_ZOMBIE + "LostHead"
        losthead_attack_name = c.NORMAL_ZOMBIE + "LostHeadAttack"
        die_name = c.NORMAL_ZOMBIE + "Die"
        boomdie_name = c.BOOMDIE

        frame_list = [
            self.helmet_walk_frames,
            self.helmet_attack_frames,
            self.walk_frames,
            self.attack_frames,
            self.losthead_walk_frames,
            self.losthead_attack_frames,
            self.die_frames,
            self.boomdie_frames,
        ]
        name_list = [
            helmet_walk_name,
            helmet_attack_name,
            walk_name,
            attack_name,
            losthead_walk_name,
            losthead_attack_name,
            die_name,
            boomdie_name,
        ]

        for i, name in enumerate(name_list):
            self.loadFrames(frame_list[i], name)

        self.frames = self.helmet_walk_frames


class FlagZombie(Zombie):
    def __init__(self, x, y, head_group):
        Zombie.__init__(self, x, y, c.FLAG_ZOMBIE, head_group)
        self.speed = 1.25

    def loadImages(self):
        self.walk_frames = []
        self.attack_frames = []
        self.losthead_walk_frames = []
        self.losthead_attack_frames = []
        self.die_frames = []
        self.boomdie_frames = []

        walk_name = self.name
        attack_name = self.name + "Attack"
        losthead_walk_name = self.name + "LostHead"
        losthead_attack_name = self.name + "LostHeadAttack"
        die_name = c.NORMAL_ZOMBIE + "Die"
        boomdie_name = c.BOOMDIE

        frame_list = [
            self.walk_frames,
            self.attack_frames,
            self.losthead_walk_frames,
            self.losthead_attack_frames,
            self.die_frames,
            self.boomdie_frames,
        ]
        name_list = [
            walk_name,
            attack_name,
            losthead_walk_name,
            losthead_attack_name,
            die_name,
            boomdie_name,
        ]

        for i, name in enumerate(name_list):
            self.loadFrames(frame_list[i], name)

        self.frames = self.walk_frames


class NewspaperZombie(Zombie):
    def __init__(self, x, y, head_group):
        Zombie.__init__(
            self,
            x,
            y,
            c.NEWSPAPER_ZOMBIE,
            head_group,
            helmet_type2_health=c.NEWSPAPER_HEALTH,
        )
        self.speed_up = False

    def loadImages(self):
        self.helmet_walk_frames = []
        self.helmet_attack_frames = []
        self.walk_frames = []
        self.attack_frames = []
        self.losthead_walk_frames = []
        self.losthead_attack_frames = []
        self.lostnewspaper_frames = []
        self.die_frames = []
        self.boomdie_frames = []

        helmet_walk_name = self.name
        helmet_attack_name = self.name + "Attack"
        walk_name = self.name + "NoPaper"
        attack_name = self.name + "NoPaperAttack"
        losthead_walk_name = self.name + "LostHead"
        losthead_attack_name = self.name + "LostHeadAttack"
        lostnewspaper_name = self.name + "LostNewspaper"
        die_name = self.name + "Die"
        boomdie_name = c.BOOMDIE

        frame_list = [
            self.helmet_walk_frames,
            self.helmet_attack_frames,
            self.walk_frames,
            self.attack_frames,
            self.losthead_walk_frames,
            self.losthead_attack_frames,
            self.lostnewspaper_frames,
            self.die_frames,
            self.boomdie_frames,
        ]
        name_list = [
            helmet_walk_name,
            helmet_attack_name,
            walk_name,
            attack_name,
            losthead_walk_name,
            losthead_attack_name,
            lostnewspaper_name,
            die_name,
            boomdie_name,
        ]

        for i, name in enumerate(name_list):
            if name in {c.BOOMDIE, lostnewspaper_name}:
                color = c.BLACK
            else:
                color = c.WHITE
            self.loadFrames(frame_list[i], name, color)

        self.frames = self.helmet_walk_frames

    def walking(self):
        if self.checkToDie(self.losthead_walk_frames):
            return

        if self.helmet_type2_health <= 0 and self.helmet_type2:
            self.changeFrames(self.lostnewspaper_frames)
            self.helmet_type2 = False
            # 触发报纸撕裂音效
            c.SOUND_NEWSPAPER_RIP.play()
        if (self.current_time - self.walk_timer) > (c.ZOMBIE_WALK_INTERVAL * self.getTimeRatio()):
            self.handleGarlicYChange()
            self.walk_timer = self.current_time
            if self.frames == self.lostnewspaper_frames:
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
                elif self.frames == self.lostnewspaper_frames and (not self.speed_up):
                    self.changeFrames(self.walk_frames)
                    self.speed_up = True
                    self.speed = 2.65
                    self.walk_animate_interval = 300
                    # 触发报纸僵尸暴走音效
                    c.SOUND_NEWSPAPER_ZOMBIE_ANGRY.play()
                    return
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


class FootballZombie(Zombie):
    def __init__(self, x, y, head_group):
        Zombie.__init__(
            self,
            x,
            y,
            c.FOOTBALL_ZOMBIE,
            head_group,
            helmet_health=c.FOOTBALL_HELMET_HEALTH,
        )
        self.speed = 1.88
        self.animate_interval = 50
        self.walk_animate_interval = 50
        self.attack_animate_interval = 60
        self.losthead_animate_interval = 180
        self.die_animate_interval = 150

    def loadImages(self):
        self.helmet_walk_frames = []
        self.helmet_attack_frames = []
        self.walk_frames = []
        self.attack_frames = []
        self.losthead_walk_frames = []
        self.losthead_attack_frames = []
        self.die_frames = []
        self.boomdie_frames = []

        helmet_walk_name = self.name
        helmet_attack_name = self.name + "Attack"
        walk_name = self.name + "LostHelmet"
        attack_name = self.name + "LostHelmetAttack"
        losthead_walk_name = self.name + "LostHead"
        losthead_attack_name = self.name + "LostHeadAttack"
        die_name = self.name + "Die"
        boomdie_name = c.BOOMDIE

        frame_list = [
            self.helmet_walk_frames,
            self.helmet_attack_frames,
            self.walk_frames,
            self.attack_frames,
            self.losthead_walk_frames,
            self.losthead_attack_frames,
            self.die_frames,
            self.boomdie_frames,
        ]
        name_list = [
            helmet_walk_name,
            helmet_attack_name,
            walk_name,
            attack_name,
            losthead_walk_name,
            losthead_attack_name,
            die_name,
            boomdie_name,
        ]

        for i, name in enumerate(name_list):
            self.loadFrames(frame_list[i], name)

        self.frames = self.helmet_walk_frames


class ScreenDoorZombie(Zombie):
    def __init__(self, x, y, head_group):
        Zombie.__init__(
            self,
            x,
            y,
            c.SCREEN_DOOR_ZOMBIE,
            head_group,
            helmet_type2_health=c.SCREEN_DOOR_HEALTH,
        )

    def loadImages(self):
        self.helmet_walk_frames = []
        self.helmet_attack_frames = []
        self.walk_frames = []
        self.attack_frames = []
        self.losthead_walk_frames = []
        self.losthead_attack_frames = []
        self.die_frames = []
        self.boomdie_frames = []

        helmet_walk_name = self.name
        helmet_attack_name = self.name + "Attack"
        walk_name = c.NORMAL_ZOMBIE
        attack_name = c.NORMAL_ZOMBIE + "Attack"
        losthead_walk_name = c.NORMAL_ZOMBIE + "LostHead"
        losthead_attack_name = c.NORMAL_ZOMBIE + "LostHeadAttack"
        die_name = c.NORMAL_ZOMBIE + "Die"
        boomdie_name = c.BOOMDIE

        frame_list = [
            self.helmet_walk_frames,
            self.helmet_attack_frames,
            self.walk_frames,
            self.attack_frames,
            self.losthead_walk_frames,
            self.losthead_attack_frames,
            self.die_frames,
            self.boomdie_frames,
        ]
        name_list = [
            helmet_walk_name,
            helmet_attack_name,
            walk_name,
            attack_name,
            losthead_walk_name,
            losthead_attack_name,
            die_name,
            boomdie_name,
        ]

        for i, name in enumerate(name_list):
            self.loadFrames(frame_list[i], name)

        self.frames = self.helmet_walk_frames
