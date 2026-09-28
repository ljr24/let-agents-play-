"""Local reports. Analysis data is never copied into model decision inputs."""
from collections import Counter
from dataclasses import asdict
import csv
import html
import json
from pathlib import Path
import time

from .controllers import rule_action, make_payload, parse_reply, ChatCompletions
from .recording import read_lines, encoded
from .schemas import validate_manifest
from .cloud_metrics import cloud_metrics
from .plant_metrics import plant_metrics


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_csv(path, rows):
    with Path(path).open("w", encoding="utf-8-sig", newline="") as stream:
        if rows:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(
                {k: encoded(v) if isinstance(v, (list, dict)) else v for k, v in row.items()}
                for row in rows
            )


def table(rows):
    if not rows:
        return "<p>没有样本。</p>"
    escape = lambda v: html.escape(encoded(v) if isinstance(v, (dict, list)) else str(v))
    return (
        '<div class="scroll"><table><thead><tr>'
        + "".join("<th>" + escape(k) + "</th>" for k in rows[0])
        + "</tr></thead><tbody>"
        + "".join(
            "<tr>" + "".join("<td>" + escape(v) + "</td>" for v in row.values()) + "</tr>"
            for row in rows
        )
        + "</tbody></table></div>"
    )


def write_html(path, title, body):
    Path(path).write_text(
        '<!doctype html><html lang="zh-CN"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1"><title>'
        + html.escape(title)
        + "</title><style>body{font:16px/1.6 system-ui;background:#edf3ed;color:#203b30;max-width:1200px;margin:32px auto;padding:20px}"
        "h1,h2{color:#164c38}table{border-collapse:collapse;background:white;min-width:100%}th,td{padding:10px;border:1px solid #ccdbcf;vertical-align:top}"
        "th{background:#d9e9de}.scroll{overflow:auto}code{background:#d9e9de;padding:3px}a{color:#086443}</style>"
        "<h1>" + html.escape(title) + "</h1>" + body + "</html>",
        encoding="utf-8",
    )


def run_metrics(directory):
    directory = Path(directory)
    manifest, result = validate_manifest(read_json(directory / "manifest.json")), read_json(
        directory / "result.json"
    )
    events = read_lines(directory / "events.jsonl")
    actions = read_lines(directory / "actions.jsonl")
    models = read_lines(directory / "model_results.jsonl")
    checkpoints = read_lines(directory / "checkpoints.jsonl")
    final = checkpoints[-1]["state"] if checkpoints else {}
    losses = Counter(
        f"{e['plant_type']}:{e['reason']}" for e in events if e["type"] == "plant_loss"
    )
    latencies = [
        m["latency_ms"] for m in models if "latency_ms" in m and m.get("error") != "TIMEOUT"
    ]
    metrics = {
        "记录": directory.name,
        "控制者": manifest["config"]["actor"],
        "关卡": manifest.get("run_identity", {}).get("level_id", manifest["config"]["scenario"]),
        "方案": manifest.get("run_identity", {}).get("scheme_id", "未分类"),
        "种子": manifest["seed"],
        "结果": result["status"] if result.get("finalized") else "technical_interruption",
        "模拟秒": result["sim_ms"] / 1000,
        "实时": manifest["realtime"],
        "执行模式": manifest.get('execution_mode', 'realtime' if manifest['realtime'] else 'offline'),
        "可纳入正式比较": bool(result.get("comparison_eligible") and result.get("finalized")),
        "标记": result.get("flags", []),
        "阳光收入": sum(e["amount"] for e in events if e["type"] == "sun_income"),
        "阳光支出": sum(e["amount"] for e in events if e["type"] == "sun_spent"),
        "植物损失": dict(losses),
        "小推车启动": sum(e["type"] == "mower_started" for e in events),
        "执行动作": len(actions),
        "失败动作": sum(not a["success"] for a in actions),
        "提交拒绝": sum(e["type"] == "action_rejected" for e in events),
        "AI平均延迟毫秒": round(sum(latencies) / len(latencies), 1) if latencies else None,
        "AI错误": dict(Counter(m["error"] for m in models if m.get("error"))),
        "实际Token": sum(
            m.get("usage", {}).get("total_tokens", 0)
            for m in models
            if isinstance(m.get("usage"), dict)
        ),
        "最终布局": [
            {"type": e["name"], "row": e["row"], "col": e["col"]}
            for e in final.get("entities", [])
            if e["kind"] == "plant"
        ],
    }
    # Stable columns for mixed human/cloud CSV reports.
    metrics.update(cloud_metrics(directory))
    metrics.update(plant_metrics(events))
    metrics.pop("实际Token", None)
    return metrics


def compare_runs(directories, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    rows = [run_metrics(p) for p in directories]
    manifests = [read_json(Path(p) / "manifest.json") for p in directories]
    matched = bool(rows) and len({m["environment_id"] for m in manifests}) == 1
    condition_match = len({m.get("condition_id", m["environment_id"]) for m in manifests}) <= 1
    actors_match = len({r["控制者"] for r in rows}) <= 1
    schemes_differ = len({r["方案"] for r in rows}) > 1
    versions_match = len({encoded(m["versions"]) for m in manifests}) <= 1
    mode_match = len({m.get('execution_mode', 'realtime' if m['realtime'] else 'offline') for m in manifests}) <= 1
    cloud_rows = [r for r in rows if r["控制者"] == "cloud"]
    controller_known = all(r["云端配置"] is not None for r in cloud_rows)
    controller_match = controller_known and len({encoded(r["云端配置"]) for r in cloud_rows}) <= 1
    eligible = (
        len(rows) >= 2
        and matched
        and versions_match
        and mode_match
        and controller_match
        and (condition_match or (schemes_differ and actors_match))
        and all(r["可纳入正式比较"] for r in rows)
    )
    summary = {
        "paired_comparison_valid": eligible,
        "same_environment": matched,
        "same_condition": condition_match,
        "comparison_kind": "cross_scheme" if schemes_differ else "same_scheme_controllers",
        "same_versions": versions_match,
        "same_execution_mode": mode_match,
        "same_cloud_controller_configuration": controller_match,
        "controller_configuration_known": controller_known,
        "comparison_note": "同方案允许控制者不同；跨方案要求控制者及云端设置相同。均要求环境、版本、时间模式一致且无干预。",
        "runs": rows,
    }
    (output / "comparison.json").write_text(encoded(summary), encoding="utf-8")
    write_csv(output / "comparison.csv", rows)
    timeline = []
    for path in directories:
        for action in read_lines(Path(path) / "actions.jsonl"):
            timeline.append(
                {
                    "run": Path(path).name,
                    "sim_ms": action["sim_ms"],
                    "action": action["action"],
                    "success": action["success"],
                    "reason": action["reason"],
                    "replay_command": f'.\\.venv\\Scripts\\python.exe -m daylab replay "{Path(path).resolve()}" --at {action["sim_ms"] / 1000:g}',
                }
            )
    write_csv(output / "action_timeline.csv", timeline)
    body = "<p>研究范围：共同可见状态下的策略与决策比较，不代表视觉感知能力完全相同。</p>"
    body += "<p>严格配对有效：<b>" + ("是" if eligible else "否（单局、版本/条件/云端配置不同或未知、未完成或受到干预）") + "</b>。不同模型仍可描述性比较，但需明确研究变量；用量未知请求不计入已确认Token，不代表免费。</p>"
    body += table(rows) + "<h2>动作时间线 / 回放定位</h2><p>复制回放命令，或在实验入口中选择记录并输入对应秒数。</p>" + table(timeline)
    body += (
        '<p><a href="comparison.csv">比较 CSV</a> · <a href="action_timeline.csv">动作时间线 CSV</a></p>'
    )
    write_html(output / "index.html", "白天实验 · 整局比较", body)
    return output / "index.html"


def decision_samples(directory):
    directory = Path(directory)
    decisions = read_lines(directory / "decisions.jsonl")
    # Exclude nominal waiting samples close to an actual decision.
    waits = [
        w
        for w in read_lines(directory / "wait_samples.jsonl")
        if not any(abs(w["sim_ms"] - d["sim_ms"]) <= 200 for d in decisions)
    ]
    return [("decision", d) for d in decisions] + [("wait", w) for w in waits]


def same_state_compare(
    directory, output, cloud_config=None, transport=None, limit=100, cancel_event=None
):
    directory, output = Path(directory), Path(output)
    manifest = validate_manifest(read_json(directory / "manifest.json"))
    source_result = read_json(directory / "result.json")
    if manifest["config"]["actor"] != "human":
        raise ValueError("Same-state comparison requires a human-controlled recording")
    output.mkdir(parents=True, exist_ok=True)
    executions = {a["command_id"]: a for a in read_lines(directory / "actions.jsonl")}
    metadata = {
        "analysis_type": "offline_same_state",
        "source_directory": str(directory.resolve()),
        "source_manifest": manifest,
        "source_result": source_result,
        "cloud_config": asdict(cloud_config) if cloud_config else None,
        "decision_policy": "single_attempt_fixed_observation",
        "repair_enabled_effective": False,
        "memory_policy": "Independent fixed-observation samples; no persistent AI strategy or reconstructed episode facts. Empty memory unless explicitly present in recorded public input.",
        "repair_policy_note": "Offline same-state comparison measures first replies only; no repair or future observations are used, regardless of realtime repair_invalid_reply.",
        "sample_limit": limit,
    }
    (output / "metadata.json").write_text(encoded(metadata), encoding="utf-8")
    transport = transport or (ChatCompletions(cloud_config) if cloud_config else None)
    rows, calls, tokens, last_request = [], 0, 0, float("-inf")
    with (output / "model_calls.jsonl").open("w", encoding="utf-8") as trace:
        for index, (kind, sample) in enumerate(
            sorted(decision_samples(directory), key=lambda s: s[1]["sim_ms"])[:limit]
        ):
            if cancel_event and cancel_event.is_set():
                break
            context = sample[
                "input"
            ]  # ONLY pre-decision public data; action label stays below this boundary
            start = time.monotonic()
            error, response, payload = None, None, None
            if cloud_config:
                from .request_limits import prepare_request, InputLimitError
                try:
                    payload, _, diagnostics = prepare_request(cloud_config, context, make_payload)
                    reservation = diagnostics["estimated_input_tokens"] + diagnostics["output_limit"]
                except InputLimitError:
                    payload, reservation = None, 0
                if (
                    payload is None or calls >= cloud_config.max_requests
                    or tokens + reservation > cloud_config.max_total_tokens
                ):
                    action, error = None, "INPUT_TOO_LARGE" if payload is None else "BUDGET_EXHAUSTED"
                else:
                    delay = max(0, last_request + cloud_config.min_interval_s - time.monotonic())
                    if cancel_event:
                        if cancel_event.wait(delay):
                            break
                    else:
                        time.sleep(delay)
                    calls += 1
                    last_request = start = time.monotonic()
                    try:
                        response = transport(payload)
                        action, error = parse_reply(response, context, cloud_config)
                    except Exception as exc:
                        action, error = None, "SERVICE_ERROR:" + type(exc).__name__
                    usage = response.get("usage") if isinstance(response, dict) else None
                    used = usage.get("total_tokens") if isinstance(usage, dict) else None
                    tokens += used if type(used) is int and used >= 0 else reservation
            else:
                action = rule_action(context["observation"])
            latency = (time.monotonic() - start) * 1000
            trace.write(
                encoded(
                    dict(
                        sample=index,
                        input=context,
                        payload=payload,
                        response=response,
                        parsed_action=action,
                        error=error,
                        latency_ms=latency,
                        budget_tokens=tokens,
                    )
                )
                + "\n"
            )
            label = sample["action"]
            execution = executions.get(sample.get("command_id"))
            outcome = (
                {k: execution[k] for k in ("sim_ms", "success", "reason", "plant_id")}
                if execution
                else None
            )
            both_place = (
                label["type"] == "PLACE_PLANT" and action and action["type"] == "PLACE_PLANT"
            )
            rows.append(
                {
                    "sample": index,
                    "group": kind,
                    "sim_ms": sample["sim_ms"],
                    "human_action": label,
                    "human_command_id": sample.get("command_id"),
                    "human_execution_result": outcome,
                    "model_action": action,
                    "error": error,
                    "latency_ms": round(latency, 2),
                    "same_action_type": bool(action and action["type"] == label["type"]),
                    "same_plant_type": action["plant_type"] == label["plant_type"]
                    if both_place
                    else None,
                    "same_row": action["row"] == label["row"] if both_place else None,
                    "same_col": action["col"] == label["col"] if both_place else None,
                    "exact_match": action == label,
                    "replay_command": f'.\\.venv\\Scripts\\python.exe -m daylab replay "{directory.resolve()}" --at {sample["sim_ms"] / 1000:g}',
                }
            )
    scores = []
    for group in ("decision", "wait"):
        selected = [r for r in rows if r["group"] == group]
        for metric in (
            "same_action_type",
            "same_plant_type",
            "same_row",
            "same_col",
            "exact_match",
        ):
            valid = [r[metric] for r in selected if r[metric] is not None]
            scores.append(
                {
                    "group": group,
                    "metric": metric,
                    "matches": sum(valid),
                    "denominator": len(valid),
                    "rate": sum(valid) / len(valid) if valid else None,
                }
            )
    write_csv(output / "decisions.csv", rows)
    write_csv(output / "scores.csv", scores)
    write_html(
        output / "index.html",
        "白天实验 · 同局面决策比较",
        "<p>离线条件决策测试；思考耗时单独列出，不混入实时对局成绩。植物和行列一致率仅以双方都选择种植的样本为分母。"
        "等待样本独立统计。模型输入中不含待比较的人类动作和未来信息。</p>"
        + "<p>来源记录状态（不送入模型）："
        + html.escape(encoded(source_result))
        + "</p>"
        + table(scores)
        + table(rows)
        + '<p><a href="decisions.csv">样本 CSV</a> · <a href="scores.csv">一致率 CSV</a> · <a href="model_calls.jsonl">完整输入与回复</a></p>',
    )
    return output / "index.html"
