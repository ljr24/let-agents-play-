"""Play responsibilities only."""
import time
from ..session import GameSession
from ..controllers import CloudController
from ..recording import ROOT
from .input import InputRouter
from .view import GameView
from ..runner import make_runner, make_controller, paused_cloud


def play(config, seed, *, cloud_config=None, render_fps=60, output_root=ROOT / "experiments"):
    import pygame as pg
    from game import assets as tool

    pausing = paused_cloud(config.actor, cloud_config)
    session = GameSession(headless=False, realtime=not pausing, output_root=output_root,
                          execution_mode='pause_think' if pausing else 'realtime')
    controller = None
    try:
        session.reset(config, seed)
        controller = make_controller(config.actor, cloud_config)
        runner = make_runner(session, controller)
        router = InputRouter(session) if config.actor == "human" else None
        view = GameView(session)
        clock = pg.time.Clock()
        last = time.monotonic()
        paused = False
        last_seq = 0
        running = True
        while running:
            now = time.monotonic()
            dt, last = now - last, now
            for event in pg.event.get():
                if event.type == pg.QUIT or (event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE):
                    running = False
                elif (
                    event.type == pg.KEYDOWN
                    and event.key == pg.K_RETURN
                    and session.status != "running"
                ):
                    running = False
                elif (
                    event.type == pg.KEYDOWN and event.key == pg.K_p and session.status == "running"
                ):
                    paused = not paused
                    session.flag("manual_pause", paused=paused)
                    dt = 0
                elif event.type == pg.KEYDOWN and event.key == pg.K_r and config.practice:
                    if controller:
                        controller.close(session)
                    session.flag("practice_restart")
                    session.reset(config, seed)
                    controller = make_controller(config.actor, cloud_config)
                    runner = make_runner(session, controller)
                    router = InputRouter(session) if config.actor == "human" else None
                    view = GameView(session)
                    dt = 0
                    paused, last_seq = False, 0
                elif not router and event.type == pg.MOUSEWHEEL:
                    view.turn_page(-event.y)
                elif router and not paused and session.status == "running":
                    router.event(event)
            if not running:
                break
            if not paused and session.status == "running":
                runner.pulse(dt, now)
            if router:
                for event in session.events(last_seq):
                    last_seq = event["seq"]
                    if event["type"] in ("action_result", "action_rejected"):
                        router.message = (
                            "操作成功" if event.get("success") else "操作未执行：" + event["reason"]
                        )
            extra = ""
            if isinstance(controller, CloudController):
                state = controller.last_error or ("等待回复" if controller.inflight else "等待下一次请求")
                extra = f"云端 | 请求 {controller.requests}/{controller.config.max_requests} | Token记账 {controller.used_tokens} | {state}"
                if pausing:
                    extra = '思考暂停模式 | ' + ('推进中 | ' if runner.remaining else '游戏已冻结 | ') + extra
            view.draw(tool.SCREEN, router, paused, extra)
            pg.display.flip()
            if session.status != "running" and not session.closed:
                if controller:
                    controller.close(session)
                session.close()
            clock.tick(render_fps)
    except Exception as exc:
        if not session.closed:
            session.log("errors", {"error": type(exc).__name__, "message": str(exc)})
            session.finish("technical_error")
        raise
    finally:
        if controller:
            controller.close(session)
        session.close("user_quit")
        pg.display.quit()
    return session.directory
