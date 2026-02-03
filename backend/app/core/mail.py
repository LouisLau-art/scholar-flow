import resend
from typing import Any, Dict, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from supabase import create_client, Client

from app.core.config import app_config, ResendConfig
from app.models.email_log import EmailStatus


class EmailService:
    def __init__(self):
        self.config = ResendConfig.from_env()
        if self.config:
            resend.api_key = self.config.api_key
        
        # Path to templates: backend/app/core/templates
        templates_dir = Path(__file__).resolve().parent / "templates"
        self._jinja = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )
        
        # Use Supabase Service Key as secret for tokens (backend-only)
        self._serializer = URLSafeTimedSerializer(app_config.supabase_key)
        
        # Service Role Client for logging (Sync client)
        self._supabase: Client = create_client(app_config.supabase_url, app_config.supabase_key)

    def is_configured(self) -> bool:
        return self.config is not None

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

    def send_email_background(self, to_email: str, subject: str, template_name: str, context: Dict[str, Any]):
        """
        Entry point for BackgroundTasks. Handles rendering, sending, retrying, and logging.
        Runs synchronously in a threadpool (FastAPI default for non-async tasks).
        """
        # 1. Render
        try:
            html_content = self.render_template(template_name, context)
        except Exception as e:
            self._log_attempt(to_email, subject, template_name, EmailStatus.FAILED, error_message=f"Template Error: {str(e)}")
            return

        # 2. Send with Retry
        if not self.is_configured():
            print(f"[Email] Resend not configured. Mock send to {to_email}: {subject}")
            self._log_attempt(to_email, subject, template_name, EmailStatus.SENT, provider_id="mock-env")
            return

        try:
            response = self._send_with_retry(to_email, subject, html_content)
            # Resend SDK v2 returns an object, try accessing 'id' attribute or dict item
            provider_id = None
            if isinstance(response, dict):
                provider_id = response.get("id")
            elif hasattr(response, "id"):
                provider_id = response.id
            
            self._log_attempt(to_email, subject, template_name, EmailStatus.SENT, provider_id=provider_id)
        except Exception as e:
            print(f"[Email] Final failure for {to_email}: {e}")
            self._log_attempt(to_email, subject, template_name, EmailStatus.FAILED, error_message=str(e))

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def _send_with_retry(self, to_email: str, subject: str, html_content: str):
        params = {
            "from": self.config.sender,
            "to": [to_email],
            "subject": subject,
            "html": html_content,
        }
        return resend.Emails.send(params)

    def _log_attempt(self, recipient: str, subject: str, template_name: str, status: EmailStatus, provider_id: Optional[str] = None, error_message: Optional[str] = None):
        try:
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