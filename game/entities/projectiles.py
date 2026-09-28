"""Original pypvz entity behavior, grouped by responsibility. See docs/UPSTREAM.md."""
import pygame as pg
from game import constants as c, assets as tool


class Bullet(pg.sprite.Sprite):
    def __init__(
        self,
        x: int,
        start_y: int,
        dest_y: int,
        name: str,
        damage: int,
        effect: str = None,
        passed_torchwood_x: int = None,
        damage_type: str = c.ZOMBIE_DEAFULT_DAMAGE,
    ):
        pg.sprite.Sprite.__init__(self)

        self.name = name
        self.frames = []
        self.frame_index = 0
        self.load_images()
        self.frame_num = len(self.frames)
        self.image = self.frames[self.frame_index]
        self.mask = pg.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = start_y
        self.dest_y = dest_y
        self.y_vel = 15 if (dest_y > start_y) else -15
        self.x_vel = 10
        self.damage = damage
        self.damage_type = damage_type
        self.effect = effect
        self.state = c.FLY
        self.current_time = 0
        self.animate_timer = 0
        self.animate_interval = 70
        self.passed_torchwood_x = passed_torchwood_x  # 记录最近通过的火炬树横坐标，如果没有缺省为None

    def loadFrames(self, frames, name):
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
            frames.append(tool.get_image(frame, x, y, width, height))

    def load_images(self):
        self.fly_frames = []
        self.explode_frames = []

        fly_name = self.name
        if self.name in c.BULLET_INDEPENDENT_BOOM_IMG:
            explode_name = f"{self.name}Explode"
        else:
            explode_name = "PeaNormalExplode"

        self.loadFrames(self.fly_frames, fly_name)
        self.loadFrames(self.explode_frames, explode_name)

        self.frames = self.fly_frames

    def update(self, game_info):
        self.current_time = game_info[c.CURRENT_TIME]
        if self.state == c.FLY:
            if self.rect.y != self.dest_y:
                self.rect.y += self.y_vel
                if self.y_vel * (self.dest_y - self.rect.y) < 0:
                    self.rect.y = self.dest_y
            self.rect.x += self.x_vel
            if self.rect.x >= c.SCREEN_WIDTH + 20:
                self.kill()
        elif self.state == c.EXPLODE:
            if (self.current_time - self.explode_timer) > 250:
                self.kill()
        if self.current_time - self.animate_timer >= self.animate_interval:
            self.frame_index += 1
            self.animate_timer = self.current_time
            if self.frame_index >= self.frame_num:
                self.frame_index = 0
            self.image = self.frames[self.frame_index]

    def setExplode(self):
        self.state = c.EXPLODE
        self.explode_timer = self.current_time
        self.frames = self.explode_frames
        self.frame_num = len(self.frames)
        self.image = self.frames[0]
        self.mask = pg.mask.from_surface(self.image)

        # 播放子弹爆炸音效
        if self.name == c.BULLET_FIREBALL:
            c.SOUND_FIREPEA_EXPLODE.play()
        else:
            c.SOUND_BULLET_EXPLODE.play()

    def draw(self, surface):
        surface.blit(self.image, self.rect)


class Fume(pg.sprite.Sprite):
    def __init__(self, x, y):
        pg.sprite.Sprite.__init__(self)
        self.name = c.FUME
        self.state = "visual"
        self.timer = 0
        self.frame_index = 0
        self.load_images()
        self.frame_num = len(self.frames)
        self.image = self.frames[self.frame_index]
        self.mask = pg.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y

    def load_images(self):
        self.fly_frames = []

        fly_name = self.name

        self.loadFrames(self.fly_frames, fly_name)

        self.frames = self.fly_frames

    def draw(self, surface):
        surface.blit(self.image, self.rect)

    def update(self, game_info):
        self.current_time = game_info[c.CURRENT_TIME]
        if self.current_time - self.timer >= 100:
            self.frame_index += 1
            if self.frame_index >= self.frame_num:
                self.frame_index = self.frame_num - 1
                self.kill()
            self.timer = self.current_time
        self.image = self.frames[self.frame_index]

    def loadFrames(self, frames, name):
        frame_list = tool.GFX[name]
        x, y = 0, 0
        rect = frame_list[0].get_rect()
        width, height = rect.w, rect.h

        for frame in frame_list:
            frames.append(tool.get_image(frame, x, y, width, height))


class StarBullet(Bullet):
    def __init__(
        self,
        x,
        start_y,
        damage,
        direction,
        level,
        damage_type=c.ZOMBIE_DEAFULT_DAMAGE,
    ):  # direction指星星飞行方向
        Bullet.__init__(
            self,
            x,
            start_y,
            start_y,
            c.BULLET_STAR,
            damage,
            damage_type=damage_type,
        )
        self.level = level
        self.map_y = self.level.map.getMapIndex(self.rect.x, self.rect.centery)[1]
        self.direction = direction

    def update(self, game_info):
        self.current_time = game_info[c.CURRENT_TIME]
        if self.state == c.FLY:
            if self.direction == c.STAR_FORWARD_UP:
                self.rect.x += 8
                self.rect.y -= 6
            elif self.direction == c.STAR_FORWARD_DOWN:
                self.rect.x += 7
                self.rect.y += 7
            elif self.direction == c.STAR_UPWARD:
                self.rect.y -= 10
            elif self.direction == c.STAR_DOWNWARD:
                self.rect.y += 10
            else:
                self.rect.x -= 10
            self.handleMapYPosition()
            if (
                (self.rect.x > c.SCREEN_WIDTH + 20)
                or (self.rect.right < -20)
                or (self.rect.y > c.SCREEN_HEIGHT)
                or (self.rect.y < 0)
            ):
                self.kill()
        elif self.state == c.EXPLODE:
            if (self.current_time - self.explode_timer) >= 250:
                self.kill()

    # 这里用的是坚果保龄球的代码改一下，实现子弹换行
    def handleMapYPosition(self):
        if self.direction == c.STAR_UPWARD:
            map_y1 = self.level.map.getMapIndex(self.rect.x, self.rect.centery + 40)[1]
        else:
            map_y1 = self.level.map.getMapIndex(self.rect.x, self.rect.centery + 20)[1]
        if (getattr(self, "lab_row", self.map_y) != map_y1) and (0 <= map_y1 <= self.level.map_y_len - 1):  # 换行
            self._lab_relocating = True
            try:
                for group in self.groups():
                    if group in self.level.bullet_groups:
                        group.remove(self)
                self.level.bullet_groups[map_y1].add(self)
            finally:
                self._lab_relocating = False
            self.map_y = map_y1
