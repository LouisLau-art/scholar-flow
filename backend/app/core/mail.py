import logging
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import unescape
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

import resend
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from jinja2 import Environment, FileSystemLoader, select_autoescape
from supabase import create_client, Client
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.core.config import SMTPConfig, app_config, ResendConfig
from app.models.email_log import EmailStatus

logger = logging.getLogger(__name__)
_TAG_TOKEN_RE = re.compile(r"[^A-Za-z0-9_-]+")
_IDEMPOTENCY_TOKEN_RE = re.compile(r"[^A-Za-z0-9_:/.\-]+")
_SPACE_RE = re.compile(r"\s+")
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_HTML_LINK_RE = re.compile(r"<a\b[^>]*href=['\"]?([^'\">\s]+)[^>]*>(.*?)</a>", flags=re.IGNORECASE | re.DOTALL)
_HTML_BREAK_RE = re.compile(r"<br\s*/?>", flags=re.IGNORECASE)
_HTML_PARAGRAPH_CLOSE_RE = re.compile(r"</(p|div|h[1-6]|section|article)>", flags=re.IGNORECASE)
_HTML_BLOCK_CLOSE_RE = re.compile(r"</(li|ul|ol|tr|table)>", flags=re.IGNORECASE)
_HTML_LIST_OPEN_RE = re.compile(r"<li\b[^>]*>", flags=re.IGNORECASE)
_SCRIPT_STYLE_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", flags=re.IGNORECASE | re.DOTALL)


def _is_retryable_resend_exception(exc: Exception) -> bool:
    """
    中文注释:
    - 仅对“可恢复”的异常重试：429 + 5xx + 网络抖动。
    - 参数校验错误（如 400/422）不重试，避免无意义重复请求。
    """
    resend_exceptions = getattr(resend, "exceptions", None)
    rate_limit_error = getattr(resend_exceptions, "RateLimitError", None)
    application_error = getattr(resend_exceptions, "ApplicationError", None)

    if rate_limit_error and isinstance(exc, rate_limit_error):
        return True
    if application_error and isinstance(exc, application_error):
        # ApplicationError 常见于 5xx 场景；若无 code 也允许重试一次链路。
        code = getattr(exc, "code", None)
        if code is None:
            return True

    try:
        code = int(getattr(exc, "code", 0) or 0)
    except Exception:
        code = 0
    if code in {429, 500, 502, 503, 504}:
        return True
    return isinstance(exc, (TimeoutError, ConnectionError))


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
        legacy = getattr(self, "config", None)
        legacy_api_key = getattr(legacy, "api_key", None) if legacy else None
        return bool(self.smtp_config or self.resend_config or legacy_api_key)

    def _effective_resend_config(self) -> ResendConfig | None:
        if self.resend_config:
            return self.resend_config
        legacy = getattr(self, "config", None)
        api_key = (getattr(legacy, "api_key", "") or "").strip() if legacy else ""
        sender = (getattr(legacy, "sender", "") or "").strip() if legacy else ""
        if not api_key:
            return None
        return ResendConfig(api_key=api_key, sender=sender or "ScholarFlow <onboarding@resend.dev>")

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

    def render_inline_template(self, template_source: str, context: Dict[str, Any]) -> str:
        return self._jinja.from_string(template_source).render(**context)

    def _normalize_idempotency_key(self, key: str | None) -> str | None:
        raw = str(key or "").strip()
        if not raw:
            return None
        normalized = _IDEMPOTENCY_TOKEN_RE.sub("-", raw).strip("-")[:256]
        return normalized or None

    def _normalize_tags(
        self, tags: Sequence[Mapping[str, str]] | None
    ) -> list[dict[str, str]] | None:
        if not tags:
            return None
        normalized: list[dict[str, str]] = []
        for item in tags:
            name = _TAG_TOKEN_RE.sub("_", str((item or {}).get("name") or "").strip())[:256]
            value = _TAG_TOKEN_RE.sub("_", str((item or {}).get("value") or "").strip())[:256]
            if not name or not value:
                continue
            normalized.append({"name": name, "value": value})
        return normalized or None

    def _merge_inline_email_tags(
        self,
        *,
        template_key: str,
        tags: Sequence[Mapping[str, str]] | None,
    ) -> list[dict[str, str]] | None:
        """
        中文注释:
        - Resend 的 tag 名称需要唯一，重复的 `template` 会直接触发 provider 错误。
        - 这里统一保证 `template` tag 只出现一次，且值始终与当前 template_key 对齐。
        """
        merged: list[dict[str, str]] = []
        seen_names: set[str] = set()
        for item in self._normalize_tags(tags) or []:
            name = str(item.get("name") or "").strip()
            if not name or name == "template" or name in seen_names:
                continue
            merged.append(item)
            seen_names.add(name)
        merged.append({"name": "template", "value": template_key})
        return merged

    def _normalize_headers(self, headers: Mapping[str, str] | None) -> dict[str, str] | None:
        if not headers:
            return None
        normalized: dict[str, str] = {}
        for raw_key, raw_value in headers.items():
            key = str(raw_key or "").strip()
            value = str(raw_value or "").strip()
            if not key or not value:
                continue
            normalized[key[:128]] = value[:1024]
        return normalized or None

    def _build_plain_text_from_html(self, html_body: str) -> str:
        def _replace_link(match: re.Match[str]) -> str:
            href = unescape(str(match.group(1) or "").strip())
            inner_html = str(match.group(2) or "")
            inner_text = _HTML_TAG_RE.sub(" ", inner_html)
            inner_text = unescape(_SPACE_RE.sub(" ", inner_text).strip())
            if inner_text and href:
                return inner_text if inner_text == href else f"{inner_text} ({href})"
            return inner_text or href

        cleaned = _SCRIPT_STYLE_RE.sub(" ", str(html_body or ""))
        cleaned = _HTML_LINK_RE.sub(_replace_link, cleaned)
        cleaned = _HTML_BREAK_RE.sub("\n", cleaned)
        cleaned = _HTML_PARAGRAPH_CLOSE_RE.sub("\n\n", cleaned)
        cleaned = _HTML_BLOCK_CLOSE_RE.sub("\n", cleaned)
        cleaned = _HTML_LIST_OPEN_RE.sub("- ", cleaned)
        cleaned = _HTML_TAG_RE.sub(" ", cleaned)
        cleaned = unescape(cleaned)
        cleaned = cleaned.replace("\r", "")
        cleaned = re.sub(r"[ \t\f\v]+", " ", cleaned)
        cleaned = re.sub(r" *\n *", "\n", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
        return cleaned[:10_000]

    def derive_plain_text_from_html(self, html_body: str) -> str:
        return self._build_plain_text_from_html(html_body)

    def render_inline_email_preview(
        self,
        *,
        subject_template: str,
        body_html_template: str,
        context: Dict[str, Any],
        body_text_template: str | None = None,
    ) -> dict[str, str]:
        """
        渲染 inline 邮件模板，返回最终 subject/html/text。

        中文注释:
        - 供“发送前预览”场景复用，避免前端自行拼接模板变量。
        - 发送链路也会复用这段逻辑，确保预览和真实发送内容一致。
        """
        subject = self.render_inline_template(subject_template, context).strip()
        html = self.render_inline_template(body_html_template, context)
        text = (
            self.render_inline_template(body_text_template, context)
            if body_text_template and str(body_text_template).strip()
            else self._build_plain_text_from_html(html)
        )
        if not subject:
            subject = "(no subject)"
        return {
            "subject": subject,
            "html": html,
            "text": text,
        }

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
        idempotency_key: str | None = None,
        tags: Sequence[Mapping[str, str]] | None = None,
        headers: Mapping[str, str] | None = None,
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
                logger.warning("[SMTP] send failed: %s", e)
                return False

        resend_cfg = self._effective_resend_config()
        if resend_cfg:
            try:
                self._send_resend_message(
                    to_email=to_email,
                    subject=subject,
                    html_body=html_body,
                    text_body=text_body,
                    sender=resend_cfg.sender,
                    idempotency_key=idempotency_key,
                    tags=tags,
                    headers=headers,
                )
                return True
            except Exception as e:
                logger.warning("[Resend] send failed: %s", e)
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
            text = self._build_plain_text_from_html(html)
        except Exception as e:
            logger.warning("[Email] template render failed: %s", e)
            return False
        return self.send_email(to_email=to_email, subject=subject, html_body=html, text_body=text)

    def send_email_background(
        self,
        to_email: str,
        subject: str,
        template_name: str,
        context: Dict[str, Any],
        *,
        idempotency_key: str | None = None,
        tags: Sequence[Mapping[str, str]] | None = None,
        headers: Mapping[str, str] | None = None,
        audit_context: Mapping[str, Any] | None = None,
    ):
        """
        Entry point for BackgroundTasks. Handles rendering, sending, retrying, and logging.
        Runs synchronously in a threadpool (FastAPI default for non-async tasks).
        """
        if not self.is_configured():
            return

        try:
            html = self.render_template(template_name, context)
            text = self._build_plain_text_from_html(html)
        except Exception as e:
            logger.warning("[Email] template render failed: %s", e)
            self._log_attempt(
                to_email,
                subject,
                template_name,
                EmailStatus.FAILED,
                error_message=str(e),
                audit_context=audit_context,
            )
            return

        # 优先 SMTP；否则走 Resend（带重试），并记录 provider_id。
        if self.smtp_config:
            ok = self.send_email(to_email=to_email, subject=subject, html_body=html, text_body=text)
            if ok:
                self._log_attempt(to_email, subject, template_name, EmailStatus.SENT, audit_context=audit_context)
            else:
                self._log_attempt(
                    to_email,
                    subject,
                    template_name,
                    EmailStatus.FAILED,
                    error_message="send failed",
                    audit_context=audit_context,
                )
            return

        resend_cfg = self._effective_resend_config()
        if not resend_cfg:
            return

        merged_tags = list(tags or [])
        merged_tags.append({"name": "template", "value": template_name})
        try:
            res = self._send_resend_message(
                to_email=to_email,
                subject=subject,
                html_body=html,
                text_body=text,
                sender=resend_cfg.sender,
                idempotency_key=idempotency_key,
                tags=merged_tags,
                headers=headers,
            )
            provider_id = (res or {}).get("id") if isinstance(res, dict) else None
            self._log_attempt(
                to_email,
                subject,
                template_name,
                EmailStatus.SENT,
                provider_id=provider_id,
                audit_context=audit_context,
            )
        except Exception as e:
            logger.warning("[Resend] send failed: %s", e)
            self._log_attempt(
                to_email,
                subject,
                template_name,
                EmailStatus.FAILED,
                error_message=str(e),
                audit_context=audit_context,
            )

    def send_inline_email_background(
        self,
        *,
        to_email: str,
        template_key: str,
        subject_template: str,
        body_html_template: str,
        context: Dict[str, Any],
        body_text_template: str | None = None,
        idempotency_key: str | None = None,
        tags: Sequence[Mapping[str, str]] | None = None,
        headers: Mapping[str, str] | None = None,
        audit_context: Mapping[str, Any] | None = None,
    ) -> None:
        """
        根据数据库模板字符串渲染并后台发送邮件。

        中文注释:
        - 用于 Admin 可配置模板（subject/html/text 均可为 Jinja 模板字符串）。
        - template_key 作为日志里的 template_name 持久化，便于追踪。
        """
        self.send_inline_email(
            to_email=to_email,
            template_key=template_key,
            subject_template=subject_template,
            body_html_template=body_html_template,
            context=context,
            body_text_template=body_text_template,
            idempotency_key=idempotency_key,
            tags=tags,
            headers=headers,
            audit_context=audit_context,
        )

    def send_inline_email(
        self,
        *,
        to_email: str,
        template_key: str,
        subject_template: str,
        body_html_template: str,
        context: Dict[str, Any],
        body_text_template: str | None = None,
        idempotency_key: str | None = None,
        tags: Sequence[Mapping[str, str]] | None = None,
        headers: Mapping[str, str] | None = None,
        audit_context: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        同步发送 inline template email，并返回真实投递结果。

        中文注释:
        - reviewer invitation 属于单条强交互动作，前端需要立刻知道 sent/failed。
        - 这里保留原有日志写入逻辑，但把结果显式返回给调用方。
        """
        result = {
            "ok": False,
            "status": EmailStatus.FAILED.value,
            "subject": "(not rendered)",
            "provider_id": None,
            "error_message": None,
        }
        if not self.is_configured():
            result["error_message"] = "Email provider is not configured"
            return result

        try:
            preview = self.render_inline_email_preview(
                subject_template=subject_template,
                body_html_template=body_html_template,
                context=context,
                body_text_template=body_text_template,
            )
            subject = preview["subject"]
            html = preview["html"]
            text = preview["text"]
            result["subject"] = subject
        except Exception as e:
            logger.warning("[Email] inline template render failed: %s", e)
            self._log_attempt(
                to_email,
                "(render failed)",
                template_key,
                EmailStatus.FAILED,
                error_message=str(e),
                audit_context=audit_context,
            )
            result["subject"] = "(render failed)"
            result["error_message"] = str(e)
            return result

        return self.send_rendered_email(
            to_email=to_email,
            template_key=template_key,
            subject=subject,
            html_body=html,
            text_body=text,
            idempotency_key=idempotency_key,
            tags=tags,
            headers=headers,
            audit_context=audit_context,
        )

    def send_rendered_email(
        self,
        *,
        to_email: str,
        template_key: str,
        subject: str,
        html_body: str,
        text_body: str | None = None,
        idempotency_key: str | None = None,
        tags: Sequence[Mapping[str, str]] | None = None,
        headers: Mapping[str, str] | None = None,
        audit_context: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        result = {
            "ok": False,
            "status": EmailStatus.FAILED.value,
            "subject": str(subject or "(no subject)").strip() or "(no subject)",
            "provider_id": None,
            "error_message": None,
        }
        if not self.is_configured():
            result["error_message"] = "Email provider is not configured"
            return result

        subject_value = result["subject"]
        text_value = text_body if text_body is not None else self._build_plain_text_from_html(html_body)

        if self.smtp_config:
            ok = self.send_email(to_email=to_email, subject=subject_value, html_body=html_body, text_body=text_value)
            if ok:
                self._log_attempt(to_email, subject_value, template_key, EmailStatus.SENT, audit_context=audit_context)
                result["ok"] = True
                result["status"] = EmailStatus.SENT.value
            else:
                self._log_attempt(
                    to_email,
                    subject_value,
                    template_key,
                    EmailStatus.FAILED,
                    error_message="send failed",
                    audit_context=audit_context,
                )
                result["error_message"] = "send failed"
            return result

        resend_cfg = self._effective_resend_config()
        if not resend_cfg:
            result["error_message"] = "Resend is not configured"
            return result

        merged_tags = self._merge_inline_email_tags(template_key=template_key, tags=tags)
        try:
            res = self._send_resend_message(
                to_email=to_email,
                subject=subject_value,
                html_body=html_body,
                text_body=text_value,
                sender=resend_cfg.sender,
                idempotency_key=idempotency_key,
                tags=merged_tags,
                headers=headers,
            )
            provider_id = (res or {}).get("id") if isinstance(res, dict) else None
            self._log_attempt(
                to_email,
                subject_value,
                template_key,
                EmailStatus.SENT,
                provider_id=provider_id,
                audit_context=audit_context,
            )
            result["ok"] = True
            result["status"] = EmailStatus.SENT.value
            result["provider_id"] = provider_id
        except Exception as e:
            logger.warning("[Resend] send failed: %s", e)
            self._log_attempt(
                to_email,
                subject_value,
                template_key,
                EmailStatus.FAILED,
                error_message=str(e),
                audit_context=audit_context,
            )
            result["error_message"] = str(e)
        return result

    def log_attempt(
        self,
        recipient: str,
        subject: str,
        template_name: str,
        status: EmailStatus,
        *,
        provider_id: Optional[str] = None,
        error_message: Optional[str] = None,
        audit_context: Mapping[str, Any] | None = None,
    ) -> None:
        self._log_attempt(
            recipient,
            subject,
            template_name,
            status,
            provider_id=provider_id,
            error_message=error_message,
            audit_context=audit_context,
        )

    def _send_resend_message(
        self,
        *,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str | None,
        sender: str,
        idempotency_key: str | None,
        tags: Sequence[Mapping[str, str]] | None,
        headers: Mapping[str, str] | None,
    ) -> dict[str, Any]:
        resend_cfg = self._effective_resend_config()
        if not resend_cfg:
            raise RuntimeError("Resend is not configured")
        resend.api_key = resend_cfg.api_key

        params = {
            "from": sender or "ScholarFlow <no-reply@scholarflow.local>",
            "to": [to_email],
            "subject": subject,
            "html": html_body,
        }
        if text_body:
            params["text"] = text_body
        normalized_headers = self._normalize_headers(headers)
        if normalized_headers:
            params["headers"] = normalized_headers
        normalized_tags = self._normalize_tags(tags)
        if normalized_tags:
            params["tags"] = normalized_tags

        options: dict[str, Any] | None = None
        normalized_key = self._normalize_idempotency_key(idempotency_key)
        if normalized_key:
            options = {"idempotency_key": normalized_key}

        return self._send_with_retry(params, options=options)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception(_is_retryable_resend_exception),
        reraise=True,
    )
    def _send_with_retry(self, params: Dict[str, Any], *, options: Dict[str, Any] | None = None):
        return resend.Emails.send(params, options)

    def _log_attempt(
        self,
        recipient: str,
        subject: str,
        template_name: str,
        status: EmailStatus,
        provider_id: Optional[str] = None,
        error_message: Optional[str] = None,
        audit_context: Mapping[str, Any] | None = None,
    ):
        try:
            if self._supabase is None:
                return
            context = dict(audit_context or {})
            data = {
                "recipient": recipient,
                "subject": subject,
                "template_name": template_name,
                "status": status.value,
                "assignment_id": str(context.get("assignment_id") or "").strip() or None,
                "manuscript_id": str(context.get("manuscript_id") or "").strip() or None,
                "actor_user_id": str(context.get("actor_user_id") or "").strip() or None,
                "idempotency_key": str(context.get("idempotency_key") or "").strip() or None,
                "scene": str(context.get("scene") or "").strip() or None,
                "event_type": str(context.get("event_type") or "").strip() or None,
                "provider_id": provider_id,
                "error_message": error_message,
                # Simple retry count tracking logic: if failed, we likely retried 2 more times (total 3).
                "retry_count": 3 if status == EmailStatus.FAILED else 0
            }
            self._supabase.table("email_logs").insert(data).execute()
        except Exception as e:
            lowered = str(e).lower()
            if (
                "email_logs.assignment_id" in lowered
                or "email_logs.manuscript_id" in lowered
                or "email_logs.actor_user_id" in lowered
                or "email_logs.idempotency_key" in lowered
                or "email_logs.scene" in lowered
                or "email_logs.event_type" in lowered
                or "schema cache" in lowered
            ):
                try:
                    fallback_data = {
                        "recipient": recipient,
                        "subject": subject,
                        "template_name": template_name,
                        "status": status.value,
                        "provider_id": provider_id,
                        "error_message": error_message,
                        "retry_count": 3 if status == EmailStatus.FAILED else 0,
                    }
                    self._supabase.table("email_logs").insert(fallback_data).execute()
                    return
                except Exception as fallback_exc:
                    logger.warning("[Email] Failed to log email attempt (fallback): %s", fallback_exc)
            logger.warning("[Email] Failed to log email attempt: %s", e)

# Global instance
email_service = EmailService()
