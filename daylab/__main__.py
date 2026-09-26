import argparse
from dataclasses import replace
import json
import time

from .config import ExperimentConfig, SCENARIOS
from .recording import ROOT, encoded


def main():
    parser = argparse.ArgumentParser(description="pypvz day_lab_v1 experiment tools")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("gui", help="Open the desktop experiment launcher")
    run = sub.add_parser("run", help="Run an independent experiment")
    run.add_argument("--actor", choices=("human", "rule", "cloud"), default="human")
    run.add_argument("--scenario", choices=SCENARIOS, default="economy")
    run.add_argument("--seed", type=int, default=42)
    run.add_argument("--headless", action="store_true")
    run.add_argument(
        "--fast", action="store_true", help="Offline rule testing, not a realtime score"
    )
    run.add_argument("--practice", action="store_true")
    run.add_argument("--cloud-config", default=str(ROOT / "cloud.local.json"))
    run.add_argument("--config", help="Optional experiment JSON, overriding scenario defaults")
    run.add_argument("--fps", type=int, default=60)
    run.add_argument("--output", default=str(ROOT / "experiments"))
    replay = sub.add_parser("replay", help="Verify or visually inspect a saved run")
    replay.add_argument("directory")
    replay.add_argument("--verify", action="store_true")
    replay.add_argument(
        "--migration-check",
        action="store_true",
        help="Compare old checkpoints without claiming same-version verification",
    )
    replay.add_argument("--at", type=float, default=0, help="Seek to simulation seconds")
    compare = sub.add_parser("compare", help="Paired full-game report")
    compare.add_argument("directories", nargs="+")
    compare.add_argument("--output", required=True)
    same = sub.add_parser("decisions", help="Offline same-state comparison of a human run")
    same.add_argument("directory")
    same.add_argument("--output", required=True)
    same.add_argument("--cloud-config")
    same.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    if args.command in (None, "gui"):
        from .ui import launcher

        launcher()
    elif args.command == "run":
        from .controllers import CloudConfig
        from .session import GameSession

        if args.fps <= 0:
            parser.error("--fps must be positive")
        if args.headless and args.actor == "human":
            parser.error("Human play requires a window")
        if args.fast and (args.actor != "rule" or not args.headless):
            parser.error("--fast is only for --headless --actor rule offline tests")
        config = ExperimentConfig(scenario=args.scenario, actor=args.actor, practice=args.practice)
        if args.config:
            with open(args.config, encoding="utf-8-sig") as stream:
                config = replace(
                    ExperimentConfig.from_dict(json.load(stream)),
                    actor=args.actor,
                    practice=args.practice,
                )
        cloud = CloudConfig.load(args.cloud_config) if args.actor == "cloud" else None
        if not args.headless:
            from .ui import play

            print(
                play(
                    config,
                    args.seed,
                    cloud_config=cloud,
                    render_fps=args.fps,
                    output_root=args.output,
                )
            )
            return
        from .runner import RealtimeRunner, make_controller

        controller = make_controller(config.actor, cloud)
        with GameSession(realtime=not args.fast, output_root=args.output) as session:
            session.reset(config, args.seed)
            last = time.monotonic()
            runner = RealtimeRunner(session, controller) if not args.fast else None
            try:
                while session.status == "running":
                    now = time.monotonic()
                    if args.fast:
                        controller.poll(session, now)
                        session.advance()
                    else:
                        runner.pulse(now - last, now)
                        last = now
                        time.sleep(0.002)
            finally:
                controller.close(session)
            print(
                encoded(
                    {
                        "status": session.status,
                        "sim_ms": session.ms,
                        "directory": str(session.directory),
                    }
                )
            )
    elif args.command == "replay":
        if args.verify or args.migration_check:
            from .replay import verify_replay

            result = verify_replay(args.directory, allow_version_mismatch=args.migration_check)
            print(encoded(result))
            if not result["state_match" if args.migration_check else "verified"]:
                raise SystemExit(1)
        else:
            from .ui import replay_window

            replay_window(args.directory, args.at)
    elif args.command == "compare":
        from .reports import compare_runs

        print(compare_runs(args.directories, args.output))
    elif args.command == "decisions":
        from .controllers import CloudConfig
        from .reports import same_state_compare

        cloud = CloudConfig.load(args.cloud_config) if args.cloud_config else None
        print(same_state_compare(args.directory, args.output, cloud, limit=args.limit))


if __name__ == "__main__":
    main()
