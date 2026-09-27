"""Editable prompts are snapshotted at config creation, not hot-reloaded mid-run."""
import hashlib
import json
from pathlib import Path
from string import Template
from .cloud_transport import strict_json

ROOT = Path(__file__).resolve().parents[1]
SLOTS = ('rules', 'cards', 'style', 'timing', 'input_format', 'output_contract')


def load_bundle(framework_file, style_file):
    def read(name):
        path = Path(name)
        return (path if path.is_absolute() else ROOT / path).read_text(encoding='utf-8-sig')
    framework = read(framework_file)
    if len(framework) > 20000:
        raise ValueError('Prompt framework too long')
    template = Template(framework)
    if set(template.get_identifiers()) != set(SLOTS) or not template.is_valid():
        raise ValueError('Prompt framework must contain the documented placeholder names')
    style = strict_json(read(style_file), max_bytes=16384)
    if not isinstance(style, dict) or set(style) != {'name', 'instructions'}:
        raise ValueError('Style requires name and instructions')
    if any(not isinstance(style[k], str) or not style[k].strip() for k in style):
        raise ValueError('Style fields must be nonempty strings')
    if len(style['name']) > 100 or len(style['instructions']) > 4000:
        raise ValueError('Style exceeds length limit')
    snapshot = dict(framework=framework, style=style)
    snapshot['sha256'] = hashlib.sha256(json.dumps(snapshot, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    return snapshot


def render_prompt(config, *, rules, cards, input_format):
    if config.decision_mode == 'pause_think':
        rules = rules.replace('AI思考时游戏继续。', '')
        timing = f'本局为思考暂停模式：等待请求/纠错时模拟时间停止；本次决策结束后推进{config.advance_after_decision_ms}毫秒，再取新观察。请求失败会记录并在无动作情况下推进，不能假定动作成功。'
    else:
        timing = '本局为实时模式：请求期间游戏继续；到达时局面可能变化，执行器再次检查时效和合法性。'
    output = ('只返回JSON对象，无Markdown、额外字段或解释。action为一个对象，只有三种形式：'
              '{"type":"PLACE_PLANT","plant_type":"Peashooter","row":0,"col":1}、'
              '{"type":"REMOVE_PLANT","plant_id":"植物完整ID"}、{"type":"WAIT"}。')
    if config.strategy_memory:
        output += f'顶层恰好有action和strategy。strategy是不超过{config.strategy_max_chars}字符的字符串，可以为空以清除旧计划。示例：{{"action":{{"type":"WAIT"}},"strategy":"等待阳光；敌人接近时重新评估"}}。'
    else:
        output += '顶层只有action。示例：{"action":{"type":"WAIT"}}。'
    bundle = config.prompt_bundle
    return Template(bundle['framework']).substitute(
        rules=rules, cards=json.dumps(cards, ensure_ascii=False, separators=(',', ':')),
        style=bundle['style']['name'] + '\n' + bundle['style']['instructions'],
        timing=timing, input_format=input_format, output_contract=output)
