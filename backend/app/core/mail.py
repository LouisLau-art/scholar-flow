import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import SMTPConfig


class EmailService:
    """
    轻量 SMTP 邮件服务（显性逻辑、可测试、可观测）

    中文注释:
    1) 发送邮件属于“非关键路径”：失败只能记录日志，不能影响主业务（投稿/分配等）。
    2) 模板渲染使用 Jinja2，将“学术英语文案”与代码分离，便于维护与审核。
    3) 不引入复杂第三方通知框架，避免黑盒与不可控重试。
    """

    def __init__(self, smtp_config: Optional[SMTPConfig] = None):
        self._smtp_config = smtp_config or SMTPConfig.from_env()

        templates_dir = Path(__file__).resolve().parents[1] / "templates" / "emails"
        self._jinja = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def is_enabled(self) -> bool:
        return self._smtp_config is not None

    def render_html(self, template_name: str, context: Dict[str, Any]) -> str:
        template = self._jinja.get_template(template_name)
        return template.render(**context)

    def send_template_email(
        self,
        *,
        to_email: str,
        subject: str,
        template_name: str,
        context: Dict[str, Any],
        text_fallback: Optional[str] = None,
    ) -> bool:
        """
        基于模板发送 HTML 邮件。

        返回值:
        - True: 发送成功
        - False: 发送失败或 SMTP 未配置（已记录日志）
        """

        if not self._smtp_config:
            print(f"[SMTP] 未配置 SMTP_HOST，跳过发送: subject={subject}, to={to_email}")
            return False

        try:
            html_body = self.render_html(template_name, context)
            return self.send_email(
                to_email=to_email,
                subject=subject,
                html_body=html_body,
                text_body=text_fallback,
            )
        except Exception as e:
            # 中文注释: 模板错误同样不能影响主业务流程
            print(f"[SMTP] 渲染/发送失败: {e}")
            return False

    def send_email(
        self,
        *,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
    ) -> bool:
        config = self._smtp_config
        if not config:
            print(f"[SMTP] 未配置 SMTP_HOST，跳过发送: subject={subject}, to={to_email}")
            return False

        # 中文注释:
        # - 使用 multipart/alternative 同时提供 text/plain 与 text/html，提升兼容性。
        # - 不把敏感配置写入日志（如 SMTP_PASSWORD）。
        msg = MIMEMultipart("alternative")
        msg["From"] = config.from_email
        msg["To"] = to_email
        msg["Subject"] = subject

        plain = text_body or "This message contains HTML content. Please use an email client that supports HTML."
        msg.attach(MIMEText(plain, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        try:
            with smtplib.SMTP(config.host, config.port, timeout=10) as server:
                if config.use_starttls:
                    server.starttls()
                if config.user and config.password:
                    server.login(config.user, config.password)
                server.sendmail(config.from_email, [to_email], msg.as_string())
            print(f"[SMTP] 发送成功: to={to_email}, subject={subject}")
            return True
        except Exception as e:
            # 中文注释: 失败只记录，不抛异常，避免阻塞/回滚主流程
            print(f"[SMTP] 发送失败: to={to_email}, subject={subject}, error={e}")
            return False

