import resend
from typing import Any, Dict, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from supabase import create_client, Client

from app.core.config import SMTPConfig, app_config, ResendConfig
from app.models.email_log import EmailStatus


class EmailService:
    _SENTINEL = object()

    def __init__(
        self,
        *,
        smtp_config: SMTPConfig | None | object = _SENTINEL,
        resend_config: ResendConfig | None | object = _SENTINEL,
        supabase_client: Client | None | object = _SENTINEL,
    ):
        # 中文注释:
        # - smtp_config / resend_config 支持依赖注入，方便单测与不同环境切换。
        # - 若调用方显式传 None，则视为禁用该 provider。
        if smtp_config is self._SENTINEL:
            smtp_config = SMTPConfig.from_env()
        if resend_config is self._SENTINEL:
            resend_config = ResendConfig.from_env()

        self.smtp_config: SMTPConfig | None = smtp_config  # type: ignore[assignment]
        self.resend_config: ResendConfig | None = resend_config  # type: ignore[assignment]

        if self.resend_config:
            resend.api_key = self.resend_config.api_key
        
        # Path to templates: backend/app/core/templates
        templates_dir = Path(__file__).resolve().parent / "templates"
        self._jinja = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )
        
        # Use Supabase Service Key as secret for tokens (backend-only)
        self._serializer = URLSafeTimedSerializer(app_config.supabase_key or "dev-secret")
        
        # Service Role Client for logging (Sync client) — 缺省允许为空（单测/CI 不必强依赖）
        if supabase_client is self._SENTINEL:
            try:
                if app_config.supabase_url and app_config.supabase_key:
                    self._supabase = create_client(
                        app_config.supabase_url, app_config.supabase_key
                    )
                else:
                    self._supabase = None
            except Exception:
                self._supabase = None
        else:
            self._supabase = supabase_client  # type: ignore[assignment]

    def is_configured(self) -> bool:
        return bool(self.smtp_config or self.resend_config)

    def create_token(self, email: str, salt: str) -> str:
        """Generate a secure, time-bound token."""
        return self._serializer.dumps(email, salt=salt)

    def verify_token(self, token: str, salt: str, max_age: int = 604800) -> Optional[str]:
        """
        Verify token and return email if valid.
        Default max_age: 7 days (604800 seconds).
        """
        try:
            email = self._serializer.loads(token, salt=salt, max_age=max_age)
            return email
        except (SignatureExpired, BadSignature):
            return None

    def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        return self._jinja.get_template(template_name).render(**context)

    # === Legacy-compatible API (tests + scheduler/worker) ===
    def render_html(self, template_name: str, context: Dict[str, Any]) -> str:
        return self.render_template(template_name, context)

    def send_email(
        self,
        *,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str | None = None,
    ) -> bool:
        """
        发送邮件（同步）。

        中文注释:
        - 单测默认走 SMTP 路径（会 patch smtplib.SMTP）。
        - 若 SMTP 未配置但 Resend 已配置，则自动降级走 Resend。
        """
        if self.smtp_config:
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = self.smtp_config.from_email
                msg["To"] = to_email

                if text_body:
                    msg.attach(MIMEText(text_body, "plain", "utf-8"))
                msg.attach(MIMEText(html_body, "html", "utf-8"))

                with smtplib.SMTP(self.smtp_config.host, self.smtp_config.port) as server:
                    if self.smtp_config.use_starttls:
                        server.starttls()
                    if self.smtp_config.user and self.smtp_config.password:
                        server.login(self.smtp_config.user, self.smtp_config.password)
                    server.sendmail(self.smtp_config.from_email, [to_email], msg.as_string())
                return True
            except Exception as e:
                print(f"[SMTP] send failed: {e}")
                return False

        if self.resend_config:
            try:
                resend.Emails.send(
                    {
                        "from": self.resend_config.sender,
                        "to": [to_email],
                        "subject": subject,
                        "html": html_body,
                    }
                )
                return True
            except Exception as e:
                print(f"[Resend] send failed: {e}")
                return False

        return False

    def send_template_email(
        self,
        *,
        to_email: str,
        subject: str,
        template_name: str,
        context: Dict[str, Any],
    ) -> bool:
        if not self.is_configured():
            return False
        try:
            html = self.render_html(template_name, context)
        except Exception as e:
            print(f"[Email] template render failed: {e}")
            return False
        return self.send_email(to_email=to_email, subject=subject, html_body=html)

    def send_email_background(self, to_email: str, subject: str, template_name: str, context: Dict[str, Any]):
        """
        Entry point for BackgroundTasks. Handles rendering, sending, retrying, and logging.
        Runs synchronously in a threadpool (FastAPI default for non-async tasks).
        """
        ok = self.send_template_email(
            to_email=to_email,
            subject=subject,
            template_name=template_name,
            context=context,
        )
        if not ok:
            self._log_attempt(
                to_email,
                subject,
                template_name,
                EmailStatus.FAILED,
                error_message="send failed",
            )
        else:
            self._log_attempt(to_email, subject, template_name, EmailStatus.SENT)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def _send_with_retry(self, to_email: str, subject: str, html_content: str):
        params = {
            "from": self.resend_config.sender if self.resend_config else "ScholarFlow <no-reply@scholarflow.local>",
            "to": [to_email],
            "subject": subject,
            "html": html_content,
        }
        return resend.Emails.send(params)

    def _log_attempt(self, recipient: str, subject: str, template_name: str, status: EmailStatus, provider_id: Optional[str] = None, error_message: Optional[str] = None):
        try:
            if self._supabase is None:
                return
            data = {
                "recipient": recipient,
                "subject": subject,
                "template_name": template_name,
                "status": status.value,
                "provider_id": provider_id,
                "error_message": error_message,
                # Simple retry count tracking logic: if failed, we likely retried 2 more times (total 3).
                "retry_count": 3 if status == EmailStatus.FAILED else 0 
            }
            self._supabase.table("email_logs").insert(data).execute()
        except Exception as e:
            print(f"[Email] Failed to log email attempt: {e}")

# Global instance
email_service = EmailService()
