import os
from dataclasses import dataclass
from typing import Optional


def _env_bool(key: str, default: bool) -> bool:
    raw = os.environ.get(key)
    if raw is None:
        return default
    lowered = raw.strip().lower()
    return lowered in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class SMTPConfig:
    """
    SMTP 配置（从环境变量读取）

    中文注释:
    1) 该配置只存在于后端进程内，严禁泄露到前端。
    2) 允许在本地/测试环境缺省（此时邮件发送逻辑会优雅降级为“只记录日志”）。
    """

    host: str
    port: int
    user: Optional[str]
    password: Optional[str]
    from_email: str
    use_starttls: bool

    @staticmethod
    def from_env() -> Optional["SMTPConfig"]:
        host = (os.environ.get("SMTP_HOST") or "").strip()
        if not host:
            return None

        port_raw = (os.environ.get("SMTP_PORT") or "587").strip()
        try:
            port = int(port_raw)
        except ValueError:
            port = 587

        user = (os.environ.get("SMTP_USER") or "").strip() or None
        password = (os.environ.get("SMTP_PASSWORD") or "").strip() or None

        from_email = (os.environ.get("SMTP_FROM_EMAIL") or user or "no-reply@scholarflow.local").strip()

        use_starttls = _env_bool("SMTP_USE_STARTTLS", True)

        return SMTPConfig(
            host=host,
            port=port,
            user=user,
            password=password,
            from_email=from_email,
            use_starttls=use_starttls,
        )


def get_admin_api_key() -> Optional[str]:
    """
    内部 Cron 接口鉴权 Key

    中文注释:
    - 仅用于 `/api/v1/internal/cron/*`，避免暴露到公网用户接口。
    - 环境变量名与 specs/011-notification-center/quickstart.md 保持一致：ADMIN_API_KEY
    """

    raw = os.environ.get("ADMIN_API_KEY")
    return raw.strip() if raw else None

