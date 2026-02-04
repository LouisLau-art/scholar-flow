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

    integrations: list[object] = [FastApiIntegration()]

    # 中文注释:
    # - 我们的后端目前主要通过 Supabase PostgREST/httpx 访问数据库，并未使用 SQLAlchemy ORM。
    # - 但 Feature 027 期望在“如果项目未来引入 SQLAlchemy”时能自动获得 DB 异常监控。
    # - 因此这里做可选启用：仅当环境里安装了 sqlalchemy 时，才挂载 SqlalchemyIntegration。
    try:
        import sqlalchemy  # noqa: F401

        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        integrations.append(SqlalchemyIntegration())
    except Exception:
        # 零崩溃原则：缺失 SQLAlchemy 不应导致 Sentry 整体不可用
        pass

    # 中文注释:
    # - HF Space / 轻量部署环境里 sentry-sdk 版本可能偏旧，部分配置项（如 with_locals/max_request_body_size）
    #   会报 "Unknown option ..."。
    # - 为了保证“零崩溃原则”同时让 Sentry 尽可能启用：先用更完整的参数初始化，
    #   若遇到未知参数则自动降级重试。
    base_options: dict[str, Any] = {
        "dsn": cfg.dsn,
        "environment": cfg.environment,
        "traces_sample_rate": cfg.traces_sample_rate,
        "integrations": integrations,
        "send_default_pii": False,
        "before_send": _before_send,
    }

    extra_options: dict[str, Any] = {
        # 不记录请求体（尤其是 multipart/pdf）
        "max_request_body_size": "never",
        # 避免把局部变量上报到云端（隐私与体积）
        "with_locals": False,
    }

    options = {**base_options, **extra_options}
    try:
        sentry_sdk.init(**options)
    except Exception as exc:
        message = str(exc)
        # 常见：ValueError("Unknown option 'with_locals'")
        # 也可能是 TypeError: got an unexpected keyword argument ...
        if "Unknown option" in message or "unexpected keyword argument" in message:
            options.pop("with_locals", None)
            options.pop("max_request_body_size", None)
            sentry_sdk.init(**options)
        else:
            raise
    return True
