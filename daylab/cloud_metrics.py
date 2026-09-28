"""Request-id based reliability metrics, including legacy records."""
from collections import Counter
from .recording import read_lines


def cloud_metrics(directory):
    requests = {r["request_id"]: r for r in read_lines(directory / "model_requests.jsonl")}
    results = {}
    result_rows = read_lines(directory / "model_results.jsonl")
    for row in result_rows:
        if row.get("request_id"):
            results[row["request_id"]] = row
    completed = [r for r in results.values() if r.get("response") is not None]
    def repair(row):
        return row.get("repair_of") or requests.get(row["request_id"], {}).get("repair_of")
    first = [r for r in completed if not repair(r)]
    retries = [r for r in completed if repair(r)]
    excluded = {"CANCELLED_AT_END", "ABANDONED_AT_END"}
    configs = read_lines(directory / "model_config.jsonl")
    config = {k: v for k, v in configs[-1].items() if k not in ("tick", "sim_ms", "event_seq", "api_key_env")} if configs else None
    usages = [r["usage"] for r in results.values() if isinstance(r.get("usage"), dict)
              and type(r["usage"].get("total_tokens")) is int and r["usage"]["total_tokens"] >= 0]
    unknown = sum(not (isinstance(results.get(key, {}).get("usage"), dict)
                  and type(results[key]["usage"].get("total_tokens")) is int
                  and results[key]["usage"]["total_tokens"] >= 0) for key in requests)
    receipt_rows = read_lines(directory / "model_submissions.jsonl")
    receipts = {r["request_id"]: r["receipt"] for r in receipt_rows}
    actions = {r["command_id"]: r for r in read_lines(directory / "actions.jsonl")}
    # Old records may not have error_stage; don't pretend unknown staging passed.
    format_errors = {"INVALID_JSON", "INVALID_SCHEMA", "INVALID_ACTION", "INVALID_COORDINATE",
                     "INVALID_TARGET", "INCOMPLETE_RESPONSE", "RESPONSE_TRUNCATED"}
    stages = [r for r in completed if r.get("error") is None or r.get("error_stage") in ("format", "observation")
              or r.get("error") in format_errors | {"DISABLED_PLANT", "OUT_OF_BOUNDS", "OCCUPIED", "INSUFFICIENT_SUN", "COOLDOWN", "TARGET_MISSING", "CARD_NOT_READY"}]
    def tokens(usage, key):
        value = usage.get(key)
        return value if type(value) is int and value >= 0 else 0
    def cached(usage):
        if "prompt_cache_hit_tokens" in usage:
            return tokens(usage, "prompt_cache_hit_tokens")
        details = usage.get("prompt_tokens_details")
        return tokens(details, "cached_tokens") if isinstance(details, dict) else 0
    return {
        "云端配置": config,
        "AI发起请求": len(requests), "AI完成回复": len(completed),
        "AI格式可评估回复": len(stages),
        "AI格式通过": sum(r.get("error") not in format_errors for r in stages),
        "AI首答数": len(first), "AI首答合法": sum(not r.get("error") for r in first),
        "AI纠错数": len(retries), "AI纠错恢复": sum(not r.get("error") for r in retries),
        "AI提交数": len(receipts) if receipt_rows else None,
        "AI提交接受": sum(r["accepted"] for r in receipts.values()) if receipt_rows else None,
        "AI执行数": sum(key in requests for key in actions),
        "AI执行成功": sum(a["success"] for key, a in actions.items() if key in requests),
        "AI错误": dict(Counter(r["error"] for r in results.values() if r.get("error") and r["error"] not in excluded)),
        "终局未采用请求": sum(r.get("error") in excluded for r in results.values()),
        "预算耗尽": any(r.get("error") == "BUDGET_EXHAUSTED" for r in result_rows),
        "已确认Token": sum(u["total_tokens"] for u in usages),
        "用量未知请求": unknown, "用量记录完整": bool(requests) and unknown == 0,
        "缓存命中Token": sum(cached(u) for u in usages),
        "输入Token": sum(tokens(u, "prompt_tokens") for u in usages),
        "输出Token": sum(tokens(u, "completion_tokens") for u in usages),
        "预算停止原因": [r.get("budget_reason", "unknown") for r in result_rows if r.get("error") == "BUDGET_EXHAUSTED"],
        "云端暂停": [dict(sim_ms=r["sim_ms"], reason=r["reason"]) for r in read_lines(directory / "model_state.jsonl") if r.get("state") == "paused"],
        "单次输入Token峰值": max((tokens(u, "prompt_tokens") for u in usages), default=None),
        "分时输入Token": [
            dict(阶段=label, 请求数=len(selected),
                 输入Token=sum(tokens(r.get("usage", {}), "prompt_tokens") for r in selected),
                 单次峰值=max((tokens(r.get("usage", {}), "prompt_tokens") for r in selected), default=None))
            for label, selected in (
                (label, [r for r in results.values() if isinstance(r.get("usage"), dict) and start <= r.get("sim_ms", 0) < end])
                for label, start, end in (("0—60秒", 0, 60000), ("60—120秒", 60000, 120000), ("120秒起", 120000, float("inf"))))
        ],
    }
