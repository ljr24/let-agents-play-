"""Shared geometry for visible cards and mouse hit testing (eight cards per page)."""
CARDS_PER_PAGE = 8
CARD_X, CARD_Y, CARD_STEP, CARD_WIDTH, CARD_HEIGHT = 94, 5, 64, 61, 88
SHOVEL_RECT = (612, 9, 78, 78)
RETRY_RECT = (185, 340, 195, 45)
END_RECT = (400, 340, 195, 45)


def card_rect(index):
    return (CARD_X + index * CARD_STEP, CARD_Y, CARD_WIDTH, CARD_HEIGHT)


def inside(point, rect):
    x, y = point
    rx, ry, w, h = rect
    return rx <= x < rx + w and ry <= y < ry + h
