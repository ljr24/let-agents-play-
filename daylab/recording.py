import hashlib
import json
import math
import platform
from importlib.metadata import distributions
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def clean(value):
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in sorted(value.items(), key=lambda p: str(p[0]))}
    if isinstance(value, (tuple, list)):
        return [clean(v) for v in value]
    if isinstance(value, set):
        return sorted((clean(v) for v in value), key=lambda v: json.dumps(v, sort_keys=True))
    return value


def encoded(value):
    return json.dumps(
        clean(value), ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
    )


def digest(value):
    return hashlib.sha256(encoded(value).encode("utf-8")).hexdigest()


def fingerprint():
    import pygame

    def hash_files(files):
        result = hashlib.sha256()
        for path in sorted(files):
            result.update(path.relative_to(ROOT).as_posix().encode())
            result.update(path.read_bytes())
        return result.hexdigest()

    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, stderr=subprocess.DEVNULL, text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        commit = "unknown"
    return {
        "commit": commit,
        "python": platform.python_version(),
        "pygame": pygame.version.ver,
        "sdl": list(pygame.get_sdl_version()),
        "dependencies": sorted(
            [d.metadata["Name"], d.version] for d in distributions() if d.metadata.get("Name")
        ),
        "lock_hash": hash_files([ROOT / "uv.lock", ROOT / "pyproject.toml"]),
        "code_hash": hash_files([*ROOT.glob("game/**/*.py"), *ROOT.glob("daylab/**/*.py")]),
        "assets_hash": hash_files(p for p in ROOT.joinpath("resources").rglob("*") if p.is_file()),
    }


class Recorder:
    def __init__(self, directory, manifest):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=False)
        self.files = {}
        self.write_json("manifest.json", manifest)

    def write_json(self, name, value):
        target = self.directory / name
        temporary = target.with_suffix(target.suffix + ".tmp")
        temporary.write_text(encoded(value) + "\n", encoding="utf-8")
        temporary.replace(target)

    def append(self, name, value):
        if name not in self.files:
            self.files[name] = (self.directory / (name + ".jsonl")).open(
                "a", encoding="utf-8", buffering=1
            )
        self.files[name].write(encoded(value) + "\n")

    def close(self):
        for stream in self.files.values():
            stream.close()
        self.files.clear()


def read_lines(path):
    path = Path(path)
    if not path.exists():
        return []
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def first_difference(left, right, path="$"):
    if type(left) != type(right):
        return {"path": path, "expected": left, "actual": right}
    if isinstance(left, dict):
        if set(left) != set(right):
            return {"path": path, "expected_keys": sorted(left), "actual_keys": sorted(right)}
        for key in sorted(left):
            found = first_difference(left[key], right[key], f"{path}.{key}")
            if found:
                return found
    elif isinstance(left, list):
        if len(left) != len(right):
            return {"path": path + ".length", "expected": len(left), "actual": len(right)}
        for i, (a, b) in enumerate(zip(left, right)):
            found = first_difference(a, b, f"{path}[{i}]")
            if found:
                return found
    elif left != right:
        return {"path": path, "expected": left, "actual": right}
    return None
