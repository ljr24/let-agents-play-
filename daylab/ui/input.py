"""Input responsibilities only."""
from .layout import CARDS_PER_PAGE, SHOVEL_RECT, card_rect, inside


class InputRouter:
    def __init__(self, session):
        self.session = session
        self.selected = None
        self.shovel = False
        self.counter = 0
        self.page = 0
        self.message = "点击卡片，再点击草地；右键取消。"

    def submit(self, action):
        self.counter += 1
        obs = self.session.observe()
        return self.session.submit(action, obs["observation_id"], f"human-{self.counter}")

    def event(self, event):
        import pygame as pg

        if event.type == pg.MOUSEWHEEL or (
            event.type == pg.KEYDOWN and event.key in (pg.K_LEFT, pg.K_RIGHT)
        ):
            direction = (
                -event.y if event.type == pg.MOUSEWHEEL else 1 if event.key == pg.K_RIGHT else -1
            )
            pages = (len(self.session.config.enabled_plants) + CARDS_PER_PAGE - 1) // CARDS_PER_PAGE
            self.page = (self.page + direction) % pages
            self.selected, self.shovel = None, False
            return
        if event.type == pg.MOUSEBUTTONDOWN:
            self.session.log(
                "raw_input",
                {"kind": "mouse_down", "position": list(event.pos), "button": event.button},
            )
            if event.button == 3:
                self.selected, self.shovel = None, False
                return
            if event.button != 1:
                return
            x, y = event.pos
            hit = next((i for i in range(CARDS_PER_PAGE) if inside((x, y), card_rect(i))), None)
            if hit is not None:
                index = self.page * CARDS_PER_PAGE + hit
                if index < len(self.session.config.enabled_plants):
                    self.selected = self.session.config.enabled_plants[index]
                    self.shovel = False
                return
            if inside((x, y), SHOVEL_RECT):
                self.shovel, self.selected = True, None
                return
            cell = self.session.cell_at(x, y - 100)
            if not 200 <= y < 675 or cell is None:
                return
            row, col = cell
            if self.shovel:
                target = self.session.observe()["grid"][row][col]
                if target:
                    self.submit({"type": "REMOVE_PLANT", "plant_id": target})
                self.shovel = False
            elif self.selected:
                self.submit(dict(type="PLACE_PLANT", plant_type=self.selected, row=row, col=col))
                self.selected = None
        elif event.type == pg.KEYDOWN:
            self.session.log("raw_input", {"kind": "key_down", "key": event.key})
            if pg.K_1 <= event.key <= pg.K_8:
                index = self.page * CARDS_PER_PAGE + event.key - pg.K_1
                if index < len(self.session.config.enabled_plants):
                    self.selected = self.session.config.enabled_plants[index]
                    self.shovel = False
            elif event.key == pg.K_s:
                self.shovel, self.selected = True, None
            elif event.key == pg.K_RETURN:
                self.submit({"type": "WAIT"})
