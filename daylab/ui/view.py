"""View responsibilities only."""
from ..config import NAMES
from .layout import CARDS_PER_PAGE, SHOVEL_RECT, RETRY_RECT, END_RECT, card_rect


class GameView:
    def __init__(self, session):
        import pygame as pg
        from game import constants as c
        from game.assets import card_image

        self.session = session
        self.page = 0
        self.font = pg.font.Font(c.FONT_PATH, 16)
        self.small = pg.font.Font(c.FONT_PATH, 12)
        self.large = pg.font.Font(c.FONT_PATH, 28)
        self.battlefield = pg.Surface((800, 600))
        self.images = {
            card["plant_type"]: card_image(card["plant_type"], card["cost"])
            for card in session.observe()["cards"]
        }

    def turn_page(self, delta):
        pages = (len(self.session.config.enabled_plants) + CARDS_PER_PAGE - 1) // CARDS_PER_PAGE
        self.page = (self.page + delta) % pages

    def draw(self, surface, router=None, paused=False, extra="", technical_pause=None):
        import pygame as pg

        session = self.session
        session.render_scene(self.battlefield)
        surface.blit(self.battlefield, (0, 100))
        pg.draw.rect(surface, (25, 50, 40), (0, 0, 800, 100))

        def text(value, pos, font=None, color=(246, 247, 221)):
            surface.blit((font or self.font).render(str(value), True, color), pos)

        text("自动阳光", (9, 8), self.small)
        text(session.sun, (9, 26), self.large, (255, 220, 85))
        text(f"{session.ms / 1000:.1f}/{session.config.max_time_ms / 1000:g}s", (9, 63), self.small)
        text(f"第 {session.wave}/{len(session.config.wave_counts)} 波", (9, 80), self.small)
        page = router.page if router else self.page
        cards = session.observe()["cards"]
        for index, card in enumerate(cards[page * CARDS_PER_PAGE : (page + 1) * CARDS_PER_PAGE]):
            x, _, width, height = card_rect(index)
            name = card["plant_type"]
            chosen = router and router.selected == name
            pg.draw.rect(
                surface,
                (105, 144, 66) if card["ready"] else (67, 78, 71),
                card_rect(index),
                border_radius=5,
            )
            if chosen:
                pg.draw.rect(surface, (255, 225, 80), card_rect(index), 3, border_radius=5)
            image = pg.transform.smoothscale(self.images[name], (40, 56))
            surface.blit(image, (x + 10, 9))
            text(NAMES[name], (x + 3, 65), self.small)
            text(
                f'{index + 1} | {card["cost"]}'
                if not card["cooldown_ms"]
                else f'{card["cooldown_ms"]/1000:.1f}s',
                (x + 9, 79),
                self.small,
            )
        pg.draw.rect(
            surface,
            (128, 107, 70) if router and router.shovel else (56, 83, 71),
            SHOVEL_RECT,
            border_radius=5,
        )
        text("铲除 [S]", (618, 34))
        text("不退款", (628, 60), self.small)
        text("P 暂停", (696, 14), self.small)
        text("Esc 结束", (696, 34), self.small)
        text("R 练习重开", (696, 54), self.small)
        text("Enter 等待", (696, 74), self.small)
        for row in range(5):
            text(row + 1, (10, 226 + row * 100), self.small, (20, 50, 30))
        for col in range(9):
            text(col + 1, (71 + col * 80, 201), self.small, (20, 50, 30))
        message = extra or (router.message if router else "AI 控制中；思考时游戏继续运行。")
        if len(cards) > CARDS_PER_PAGE:
            message = f"卡组 {page + 1}/{(len(cards) + CARDS_PER_PAGE - 1)//CARDS_PER_PAGE} 页 [左右键/滚轮] | " + message
        pg.draw.rect(surface, (25, 50, 40), (0, 675, 800, 25))
        text(message[:68], (20, 680), self.small, (255, 255, 240))
        if paused or technical_pause or session.status != "running":
            shade = pg.Surface((800, 700), pg.SRCALPHA)
            shade.fill((12, 30, 20, 185))
            surface.blit(shade, (0, 0))
            labels = {"victory": "胜利", "defeat": "战败", "timeout": "达到时限（不计战败）"}
            title = "云端暂停 · 等待处理" if technical_pause else "暂停 · 本局已标记干预" if paused else labels.get(session.status, session.status)
            text(title, (185, 245), self.large)
            if technical_pause:
                text(technical_pause[:65], (130, 298), self.small)
                for rect, label in ((RETRY_RECT, "重试并继续 [T]"), (END_RECT, "结束并保存 [Esc]")):
                    pg.draw.rect(surface, (68, 103, 80), rect, border_radius=5)
                    text(label, (rect[0] + 12, rect[1] + 12))
            else:
                text("P 继续" if paused else "记录已保存。按 Enter / Esc 返回入口。", (185, 305))
