"""Versioned public text-board presentation; never reads internal game state."""
import json


BOARD_HELP = """
Input format: text_board_v2. Read frames in chronological order; only CURRENT is actionable.
Rows/columns are zero based. Board cells use plant aliases; '.' is no plant.
Enemies are a separate lane list, not grid occupants: multiple enemies can overlap plants
or each other. x/y are sprite top-left pixels, NOT hitboxes or planting columns.
Smaller enemy x means nearer the left/home. Exact current public details follow the board.
Past frames summarize layout, visible enemies, sun, wave and mowers; they omit past
projectiles, detailed plant animation and past card cooldowns, but retain sleep/wake markers.
This is not lossless history. wave is current/total; time_limit_ms and remaining_time_ms
are public game limits, not future spawn information. '?' means absent in older records.
Markers: 睡=sleeping, 唤醒中=waking, 醒=awake, 退缩=cowering,
准备=mine unarmed, 就绪=mine armed. Sleeping/waking mushrooms cannot attack yet;
awake does not imply currently firing. A cowering ScaredyShroom does not shoot.
Use CURRENT cards ready=true, current empty plant cells, and exact plant IDs for removal.
CoffeeBean is the exception: target an existing sleeping mushroom that is not waking.
Terrain crater is unplantable. Coffee overlays never replace the mushroom's grid ID.
Tables have a header followed by JSON arrays in that column order. null means unknown.
Follow the output protocol, including strategy when required; do not return a board or prose.
"""

ALIASES = {"SunFlower": "葵", "Peashooter": "豌", "WallNut": "坚",
           "SnowPea": "冰", "RepeaterPea": "双", "CherryBomb": "樱",
           "Threepeater": "三", "StarFruit": "星", "TorchWood": "炬", "PotatoMine": "雷",
           "TallNut": "高", "Spikeweed": "刺", "Squash": "窝", "Jalapeno": "椒",
           "FumeShroom": "喷", "CoffeeBean": "咖", "ScaredyShroom": "胆", "DoomShroom": "毁"}


def legend(cards):
    # Unknown/extended content keeps its exact type; never silently drops it.
    return "\n棋盘图例：" + "，".join(
        f"{ALIASES.get(c['plant_type'], c['plant_type'])}={c['plant_type']}"
        for c in cards) + "；.=无植物。敌人另列，不能据棋盘空格判断该处没有敌人。\n"


def _json(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def _table(title, rows, columns):
    return [title + " " + ",".join(columns)] + [
        _json([r.get(k) for k in columns]) for r in rows] + ([] if rows else ["(none)"])


def _frame(obs, current):
    lines = [f"[{ 'CURRENT 当前' if current else 'PAST 过去'} t={obs['sim_ms']}ms]",
             f"sun={obs['sun']} wave={obs['wave']}/{obs.get('total_waves', '?')} status={obs['status']}",
             f"time_limit_ms={obs.get('time_limit_ms', '?')} remaining_time_ms={obs.get('remaining_time_ms', '?')}",
             "植物棋盘 col: " + " | ".join(map(str, range(obs['cols'])))]
    plants = {p['id']: p for p in obs['plants']}
    for row, cells in enumerate(obs['grid']):
        names = ["." if pid is None else _cell_label(plants.get(pid, {})) for pid in cells]
        lines.append(f"row {row}: " + " | ".join(names))
    lines += _table("敌人（同一行可有多只）", sorted(obs['zombies'], key=lambda z: (z['row'], z['x'], z['id'])),
                    ['id', 'type', 'row', 'x', 'y', 'state', 'armored', 'shield', 'slowed', 'lost_head', 'jumping', 'jumped', 'paper_broken'])
    lines += _table("小推车", obs['mowers'], ['id', 'row', 'x', 'y', 'state'])
    if current:
        lines += _table("植物详情（铲除使用id）", obs['plants'],
                        ['id', 'type', 'row', 'col', 'x', 'y', 'state', 'appearance', 'sleeping', 'waking', 'armed'])
        lines += _table("咖啡覆盖物", obs.get('overlays', []), ['id', 'row', 'col', 'target_id'])
        lines.append("不可种植弹坑(row,col): " + _json([
            [r, c] for r, row in enumerate(obs.get('terrain', []))
            for c, value in enumerate(row) if value != 'grass']))
        lines += _table("可见子弹", obs['bullets'], ['id', 'type', 'row', 'x', 'y', 'state'])
        lines += _table("当前卡片", obs['cards'], ['plant_type', 'cost', 'cooldown_ms', 'ready'])
        lines.append("ready=false: cooldown_ms>0 means cooling; sun<cost means insufficient sun; both may apply.")
        lines.append(f"observation_id={obs['observation_id']} tick={obs['tick']}")
    return lines


def _cell_label(plant):
    name = plant.get('type', 'occupied')
    label = ALIASES.get(name, name)
    if plant.get('waking'):
        marker = '唤醒中'
    elif plant.get('sleeping'):
        marker = '睡'
    elif name == 'ScaredyShroom' and plant.get('state') == 'cry':
        marker = '退缩'
    elif name in ('FumeShroom', 'ScaredyShroom', 'DoomShroom') and plant.get('sleeping') is False:
        marker = '醒'
    elif name == 'PotatoMine' and 'armed' in plant:
        marker = '就绪' if plant['armed'] else '准备'
    else:
        marker = None
    return label + (f'〔{marker}〕' if marker else '')


def board_context(context):
    """All supplied past frames (<=5s), then current; no dialogue accumulation."""
    obs = context['observation']
    lines = ['text_board_v2; 时间单位毫秒；只根据最后的 CURRENT 决策。']
    for frame in sorted(context.get('history', []), key=lambda o: o['sim_ms']):
        if obs['sim_ms'] - 5000 <= frame['sim_ms'] < obs['sim_ms']:
            lines.extend(_frame(frame, False))
    lines += ['近期已执行动作（不是待执行命令）', _json(context.get('past_actions', []))]
    lines.extend(_frame(obs, True))
    return '\n'.join(lines)
