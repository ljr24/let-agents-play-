"""Explicit Pygame/image/audio initialization. Importing this module opens no window."""
import os
import pygame as pg
from . import constants as c


def get_image(
    sheet: pg.Surface,
    x: int,
    y: int,
    width: int,
    height: int,
    colorkey: tuple[int] = c.BLACK,
    scale: int = 1,
) -> pg.Surface:
    # 不保留alpha通道的图片导入
    image = pg.Surface([width, height])
    rect = image.get_rect()

    image.blit(sheet, (0, 0), (x, y, width, height))
    if colorkey:
        image.set_colorkey(colorkey)
    image = pg.transform.scale(image, (int(rect.width * scale), int(rect.height * scale)))
    return image


def get_image_alpha(
    sheet: pg.Surface,
    x: int,
    y: int,
    width: int,
    height: int,
    colorkey: tuple[int] = c.BLACK,
    scale: int = 1,
) -> pg.Surface:
    # 保留alpha通道的图片导入
    image = pg.Surface([width, height], pg.SRCALPHA)
    rect = image.get_rect()

    image.blit(sheet, (0, 0), (x, y, width, height))
    image.set_colorkey(colorkey)
    image = pg.transform.scale(image, (int(rect.width * scale), int(rect.height * scale)))
    return image


def load_image_frames(
    directory: str, image_name: str, colorkey: tuple[int], accept: tuple[str]
) -> list[pg.Surface]:
    frame_list = []
    tmp = {}
    # image_name is "Peashooter", pic name is "Peashooter_1", get the index 1
    index_start = len(image_name) + 1
    frame_num = 0
    for pic in os.listdir(directory):
        name, ext = os.path.splitext(pic)
        if ext.lower() in accept:
            index = int(name[index_start:])
            img = pg.image.load(os.path.join(directory, pic))
            if img.get_alpha():
                img = img.convert_alpha()
            else:
                img = img.convert()
                img.set_colorkey(colorkey)
            tmp[index] = img
            frame_num += 1

    for i in range(frame_num):  # 这里注意编号必须连续，否则会出错
        frame_list.append(tmp[i])
    return frame_list


# colorkeys 是设置图像中的某个颜色值为透明,这里用来消除白边
def load_all_gfx(
    directory: str,
    colorkey: tuple[int] = c.WHITE,
    accept: tuple[str] = (".png", ".jpg", ".bmp", ".gif", ".webp"),
) -> dict[str : pg.Surface]:
    graphics = {}
    for name1 in os.listdir(directory):
        # subfolders under the folder resources\graphics
        dir1 = os.path.join(directory, name1)
        if os.path.isdir(dir1):
            for name2 in os.listdir(dir1):
                dir2 = os.path.join(dir1, name2)
                if os.path.isdir(dir2):
                    # e.g. subfolders under the folder resources\graphics\Zombies
                    for name3 in os.listdir(dir2):
                        dir3 = os.path.join(dir2, name3)
                        # e.g. subfolders or pics under the folder resources\graphics\Zombies\ConeheadZombie
                        if os.path.isdir(dir3):
                            # e.g. it"s the folder resources\graphics\Zombies\ConeheadZombie\ConeheadZombieAttack
                            image_name, _ = os.path.splitext(name3)
                            graphics[image_name] = load_image_frames(
                                dir3, image_name, colorkey, accept
                            )
                        else:
                            # e.g. pics under the folder resources\graphics\Plants\Peashooter
                            image_name, _ = os.path.splitext(name2)
                            graphics[image_name] = load_image_frames(
                                dir2, image_name, colorkey, accept
                            )
                            break
                else:
                    # e.g. pics under the folder resources\graphics\Screen
                    name, ext = os.path.splitext(name2)
                    if ext.lower() in accept:
                        img = pg.image.load(dir2)
                        if img.get_alpha():
                            img = img.convert_alpha()
                        else:
                            img = img.convert()
                            img.set_colorkey(colorkey)
                        graphics[name] = img
    return graphics


SCREEN = None
GFX = {}


def card_image(name, cost):
    """Card artwork only. No independent resource or cooldown state in the view."""
    info = c.PLANT_CARD_INFO[c.PLANT_CARD_INDEX[name]]
    frame = GFX[info[c.CARD_INDEX]]
    image = get_image(frame, 0, 0, *frame.get_size(), c.BLACK, 0.5)
    label = pg.font.Font(c.FONT_PATH, 12).render(str(cost), True, c.BLACK)
    image.blit(label, (32 - label.get_width(), 52))
    return image


def initialize(headless=False, muted=False, size=None):
    """Initialize explicitly. Importing game modules does not open a window."""
    global SCREEN
    if headless and not pg.display.get_init():
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
    if not pg.get_init():
        pg.init()
    elif not pg.display.get_init():
        pg.display.init()
    size = size or c.SCREEN_SIZE
    existing = pg.display.get_surface()
    if existing and existing.get_size() != size:
        # Releasing the SDL renderer before resizing avoids a second SCALED renderer.
        pg.display.quit()
        pg.display.init()
    if not pg.display.get_surface():
        flags = 0 if headless or pg.display.get_driver() == "dummy" else pg.SCALED
        SCREEN = pg.display.set_mode(size, flags)
    else:
        SCREEN = pg.display.get_surface()
    pg.display.set_caption(c.ORIGINAL_CAPTION)
    c.LazySound.muted = muted or headless
    if pg.mixer.get_init():
        pg.mixer.set_num_channels(255)
    if not GFX:
        GFX.update(load_all_gfx(c.PATH_IMG_DIR))
    if not headless and os.path.exists(c.ORIGINAL_LOGO):
        pg.display.set_icon(pg.image.load(c.ORIGINAL_LOGO))
    return SCREEN
