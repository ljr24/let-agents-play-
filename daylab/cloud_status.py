"""User-facing diagnostics, separate from stable machine-readable error codes."""
LABELS = {
    "TIMEOUT": "服务回复超时", "TIMEOUT_LATE_REPLY": "回复超过时限，未采用",
    "CONNECTION_ERROR": "无法连接云端服务", "INVALID_JSON": "模型回复不是完整JSON",
    "INVALID_SCHEMA": "模型回复字段不符合动作协议", "RESPONSE_TRUNCATED": "模型输出被截断",
    "INPUT_TOO_LARGE": "当前局面仍超过输入或上下文上限，请调整云端配置",
    "REQUEST_LIMIT": "整局调用次数已达上限",
    "TOKEN_BUDGET": "剩余整局Token预算不足以发起下一次请求",
    "TOKEN_BUDGET_WITH_UNKNOWN_RESERVES": "整局预算不足，包含未返回用量请求的预留",
    "HTTP_400": "服务拒绝参数，请检查模型、上下文和输出上限",
    "HTTP_401": "API密钥无效", "HTTP_402": "服务账户余额不足",
    "HTTP_403": "服务访问被拒绝", "HTTP_404": "服务地址或模型不存在",
    "HTTP_429": "云端服务限流", "HTTP_500": "云端服务内部错误",
    "HTTP_503": "云端服务暂不可用",
}


def describe(reason):
    return LABELS.get(reason, reason or "")
