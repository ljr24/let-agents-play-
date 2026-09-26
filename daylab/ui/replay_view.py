"""Replay view responsibilities only."""
from .view import GameView


def replay_window(directory, at=0, *, migration_check=False):
    import pygame as pg
    from game import assets as tool
    from ..replay import ReplayPlayer

    player = ReplayPlayer(directory, headless=False, allow_version_mismatch=migration_check)
    player.seek(at * 1000)
    view = GameView(player.session)
    paused, speed, running = True, 1, True
    clock = pg.time.Clock()
    accumulated = 0
    try:
        while running:
            dt = clock.tick(60) / 1000
            for event in pg.event.get():
                if event.type == pg.QUIT or (event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE):
                    running = False
                elif event.type == pg.MOUSEWHEEL:
                    view.turn_page(-event.y)
                elif event.type == pg.KEYDOWN:
                    if event.key == pg.K_SPACE:
                        paused = not paused
                    elif event.key in (pg.K_PLUS, pg.K_EQUALS, pg.K_KP_PLUS):
                        speed = min(32, speed * 2)
                    elif event.key in (pg.K_MINUS, pg.K_KP_MINUS):
                        speed = max(1, speed // 2)
                    elif event.key in (pg.K_LEFT, pg.K_RIGHT):
                        player.seek(
                            player.session.ms + (5000 if event.key == pg.K_RIGHT else -5000)
                        )
                        view = GameView(player.session)
            if not paused:
                accumulated += dt * speed
                while accumulated >= 0.020:
                    accumulated -= 0.020
                    if not player.step():
                        paused = True
                        break
            extra = f"回放 {speed}x | 空格播放/暂停 | 左右跳转5秒 | +/-变速 | 检查点 {player.verified}"
            if player.version_differences:
                extra = f"跨版本检查（非同版本验证）| {speed}x | 检查点 {player.verified}"
            if player.difference:
                extra = "校验失败：" + str(player.difference)
            view.draw(tool.SCREEN, extra=extra)
            pg.display.flip()
    finally:
        player.close()
        pg.display.quit()
