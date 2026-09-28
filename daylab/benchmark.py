"""Versioned benchmark definitions, shared by desktop, CLI and Python callers."""
import json
import re
from pathlib import Path

DEFINITION_PATH = Path(__file__).resolve().parents[1] / 'configs' / 'benchmark_v1.json'


def definitions():
    return json.loads(DEFINITION_PATH.read_text(encoding='utf-8'))


def load_benchmark(level_id='01', scheme_id='A', *, actor='human', practice=False):
    from .config import ExperimentConfig
    data = definitions()
    level_id, scheme_id = str(level_id).zfill(2), str(scheme_id).upper()
    if level_id not in data['levels'] or scheme_id not in data['schemes']:
        raise ValueError('请选择关卡01—10与方案A/B/C')
    codes = data['zombie_codes']
    waves = []
    for expression in data['levels'][level_id]:
        counts = {}
        for term in expression.split('+'):
            match = re.fullmatch(r'(\d*)([NCBRSPF])', term)
            if not match or match[2] not in codes:
                raise ValueError('Invalid wave definition: ' + term)
            counts[match[2]] = counts.get(match[2], 0) + int(match[1] or 1)
        waves.append(tuple(name for code, name in codes.items() for _ in range(counts.get(code, 0))))
    plants = tuple(data['schemes'][scheme_id]['plants'])
    if len(plants) != 8 or len(set(plants)) != 8:
        raise ValueError('Benchmark schemes require eight distinct cards')
    return ExperimentConfig(
        scenario='benchmark', level_id=level_id, scheme_id=scheme_id,
        benchmark_version=data['version'], enabled_plants=plants,
        enabled_zombies=tuple(codes.values()), wave_counts=tuple(map(len, waves)),
        wave_types=tuple(waves), actor=actor, practice=practice,
    )
