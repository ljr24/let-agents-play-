"""Single entry point for run identity, directory layout and discovery."""
from datetime import datetime
import json
from pathlib import Path
from .recording import digest


def identity(config):
    return dict(level_id=config.level_id or config.scenario,
                scheme_id=config.scheme_id or "custom-" + digest(list(config.enabled_plants))[:8],
                benchmark_version=config.benchmark_version or config.profile,
                controller_kind={"cloud": "agent-cloud", "rule": "agent-rule"}.get(config.actor, config.actor))


def run_directory(root, config, seed, episode_id):
    info = identity(config)
    name = f"{datetime.now():%Y%m%d-%H%M%S}_{info['controller_kind']}_seed{seed}_{episode_id[:8]}"
    return Path(root) / ("关卡" + info["level_id"]) / ("方案" + info["scheme_id"]) / name


def discover_runs(root):
    rows = []
    for path in Path(root).rglob("manifest.json"):
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
            if "config" not in manifest:
                continue
            result_path = path.parent / "result.json"
            result = json.loads(result_path.read_text(encoding="utf-8")) if result_path.exists() else {}
            info = manifest.get("run_identity", {})
            rows.append(dict(directory=path.parent, manifest=manifest, result=result,
                             level_id=info.get("level_id", manifest["config"].get("scenario", "未分类")),
                             scheme_id=info.get("scheme_id", "未分类"),
                             actor=manifest["config"]["actor"]))
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return sorted(rows, key=lambda row: row["manifest"].get("created_at", ""), reverse=True)
