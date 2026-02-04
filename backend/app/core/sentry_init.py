from typing import Any

from app.core.config import SentryConfig

_SENSITIVE_KEYS = {
    "password",
    "pass",
    "pwd",
    "access_token",
    "refresh_token",
    "token",
    "jwt",
    "authorization",
    "cookie",
    "set-cookie",
    "supabase_key",
    "service_role",
    "service_role_key",
}


def _looks_like_pdf_bytes(value: Any) -> bool:
    if isinstance(value, (bytes, bytearray)):
        head = bytes(value[:8])
        return head.startswith(b"%PDF-")
    if isinstance(value, str):
        # 避免把超长文本（可能是 base64/pdf text dump）送到 sentry
        return len(value) > 5000
    return False


def _scrub(value: Any) -> Any:
    """
    隐私清洗：递归去除敏感字段与潜在 PDF/大段文本内容。

    中文注释:
    - 目标不是“完美还原请求”，而是保证不上传明文密码与文档内容。
    """
    if _looks_like_pdf_bytes(value):
        return "[Filtered]"

    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k, v in value.items():
            key_lower = str(k).strip().lower()
            if key_lower in _SENSITIVE_KEYS:
                out[str(k)] = "[Filtered]"
                continue
            out[str(k)] = _scrub(v)
        return out

    if isinstance(value, (list, tuple)):
        return [_scrub(v) for v in value]

    return value


def _before_send(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any] | None:
    # 中文注释: 严格不上传请求体（尤其是 multipart/pdf），只保留必要的诊断信息。
    request = event.get("request")
    if isinstance(request, dict):
        headers = request.get("headers")
        if isinstance(headers, dict):
            filtered_headers: dict[str, Any] = {}
            for k, v in headers.items():
                if str(k).strip().lower() in _SENSITIVE_KEYS:
                    continue
                filtered_headers[k] = v
            request["headers"] = filtered_headers

        if "cookies" in request:
            request["cookies"] = "[Filtered]"
        if "data" in request:
            request["data"] = "[Filtered]"
        if "body" in request:
            request["body"] = "[Filtered]"

        event["request"] = request

    # 中文注释: 进一步清洗 contexts/extra 中可能被开发者手动塞入的敏感字段
    for section in ("extra", "contexts"):
        obj = event.get(section)
        if isinstance(obj, dict):
            event[section] = _scrub(obj)

    return event


def init_sentry() -> bool:
    """
    初始化 Sentry（Feature 027）。

    零崩溃原则：
    - 若未配置 DSN / 显式禁用，则直接返回 False。
    - 任何初始化异常都应在调用方 try/except 处理，不得阻塞启动。
    """
    cfg = SentryConfig.from_env()
    if not cfg.enabled:
        return False
    if not cfg.dsn:
        return False

    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

    sentry_sdk.init(
        dsn=cfg.dsn,
        environment=cfg.environment,
        traces_sample_rate=cfg.traces_sample_rate,
        integrations=[
            FastApiIntegration(),
            SqlalchemyIntegration(),
        ],
        send_default_pii=False,
        with_locals=False,
        before_send=_before_send,
        max_request_body_size="never",
    )
    return True
