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
class AppConfig:
    """
    Application Environment Config (Feature 019)
    """
    env: str  # 'development', 'staging', 'production'
    is_staging: bool
    supabase_url: str
    supabase_key: str

    @staticmethod
    def from_env() -> "AppConfig":
        env = (os.environ.get("APP_ENV") or "development").strip().lower()
        is_staging = env == "staging"
        
        # In Staging mode, we expect dedicated DB variables if provided, 
        # otherwise fallback to standard SUPABASE_URL but allow logic differentiation.
        # Feature 019 requirement: Separate DB for Staging.
        # We can either use a separate env var STAGING_SUPABASE_URL or just swap SUPABASE_URL at the platform level (Vercel/Docker).
        # Assuming platform-level swap for simplicity, so we just read SUPABASE_URL.
        
        supabase_url = (os.environ.get("SUPABASE_URL") or "").strip()
        supabase_key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()

        return AppConfig(
            env=env,
            is_staging=is_staging,
            supabase_url=supabase_url,
            supabase_key=supabase_key
        )

# Global Config Instance
app_config = AppConfig.from_env()


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

        from_email = (
            os.environ.get("SMTP_FROM_EMAIL") or user or "no-reply@scholarflow.local"
        ).strip()

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


@dataclass(frozen=True)
class MatchmakingConfig:
    """
    本地审稿人匹配（Feature 012）配置

    中文注释:
    1) 模型推理严格在本地执行（不走 OpenAI/Claude）。
    2) 阈值/TopK/冷启动门槛必须可配置，避免硬编码。
    """

    model_name: str
    threshold: float
    top_k: int
    min_reviewers: int

    @staticmethod
    def from_env() -> "MatchmakingConfig":
        model_name = (
            os.environ.get("MATCHMAKING_MODEL_NAME")
            or "sentence-transformers/all-MiniLM-L6-v2"
        ).strip()

        threshold_raw = (os.environ.get("MATCHMAKING_THRESHOLD") or "0.70").strip()
        try:
            threshold = float(threshold_raw)
        except ValueError:
            threshold = 0.70

        top_k_raw = (os.environ.get("MATCHMAKING_TOP_K") or "5").strip()
        try:
            top_k = int(top_k_raw)
        except ValueError:
            top_k = 5

        min_reviewers_raw = (os.environ.get("MATCHMAKING_MIN_REVIEWERS") or "5").strip()
        try:
            min_reviewers = int(min_reviewers_raw)
        except ValueError:
            min_reviewers = 5

        return MatchmakingConfig(
            model_name=model_name,
            threshold=threshold,
            top_k=top_k,
            min_reviewers=min_reviewers,
        )


@dataclass(frozen=True)
class CrossrefConfig:
    """
    Crossref DOI 注册 (Feature 015) 配置
    """

    depositor_email: str
    depositor_password: str
    doi_prefix: str
    api_url: str
    journal_title: str
    journal_issn: Optional[str]

    @staticmethod
    def from_env() -> Optional["CrossrefConfig"]:
        depositor_email = (os.environ.get("CROSSREF_DEPOSITOR_EMAIL") or "").strip()
        if not depositor_email:
            # 允许为空，此时 DOI 功能不可用
            return None

        depositor_password = (
            os.environ.get("CROSSREF_DEPOSITOR_PASSWORD") or ""
        ).strip()
        doi_prefix = (os.environ.get("CROSSREF_DOI_PREFIX") or "10.12345").strip()
        api_url = (
            os.environ.get("CROSSREF_API_URL")
            or "https://test.crossref.org/servlet/deposit"
        ).strip()
        journal_title = (
            os.environ.get("JOURNAL_TITLE") or "Scholar Flow Journal"
        ).strip()
        journal_issn = (os.environ.get("JOURNAL_ISSN") or "").strip() or None

        return CrossrefConfig(
            depositor_email=depositor_email,
            depositor_password=depositor_password,
            doi_prefix=doi_prefix,
            api_url=api_url,
            journal_title=journal_title,
            journal_issn=journal_issn,
        )


@dataclass(frozen=True)
class ResendConfig:
    """
    Resend API Configuration (Feature 025 - Production Email)
    """
    api_key: str
    sender: str

    @staticmethod
    def from_env() -> Optional["ResendConfig"]:
        api_key = (os.environ.get("RESEND_API_KEY") or "").strip()
        if not api_key:
            return None
        
        sender = (
            os.environ.get("EMAIL_SENDER") or "ScholarFlow <onboarding@resend.dev>"
        ).strip()
        
        return ResendConfig(api_key=api_key, sender=sender)
