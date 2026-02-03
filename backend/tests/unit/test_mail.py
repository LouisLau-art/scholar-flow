from unittest.mock import MagicMock, patch

from app.core.config import SMTPConfig
from app.core.mail import EmailService


def _smtp_config() -> SMTPConfig:
    return SMTPConfig(
        host="smtp.example.com",
        port=587,
        user="user@example.com",
        password="secret",
        from_email="no-reply@example.com",
        use_starttls=True,
    )


def test_send_email_success():
    service = EmailService(smtp_config=_smtp_config())
    with patch("app.core.mail.smtplib.SMTP") as smtp:
        server = MagicMock()
        smtp.return_value.__enter__.return_value = server

        ok = service.send_email(
            to_email="to@example.com",
            subject="Test Subject",
            html_body="<p>Hello</p>",
            text_body="Hello",
        )
        assert ok is True
        server.starttls.assert_called_once()
        server.login.assert_called_once()
        server.sendmail.assert_called_once()


def test_send_email_failure_does_not_raise():
    service = EmailService(smtp_config=_smtp_config())
    with patch("app.core.mail.smtplib.SMTP") as smtp:
        server = MagicMock()
        server.sendmail.side_effect = RuntimeError("smtp down")
        smtp.return_value.__enter__.return_value = server

        ok = service.send_email(
            to_email="to@example.com",
            subject="Test Subject",
            html_body="<p>Hello</p>",
        )
        assert ok is False


def test_send_email_returns_false_when_smtp_not_configured():
    service = EmailService(smtp_config=None)
    assert (
        service.send_email(to_email="to@example.com", subject="s", html_body="<p>x</p>")
        is False
    )


def test_send_template_email_returns_false_when_smtp_not_configured():
    service = EmailService(smtp_config=None)
    ok = service.send_template_email(
        to_email="to@example.com",
        subject="s",
        template_name="anything.html",
        context={},
    )
    assert ok is False


def test_send_template_email_handles_render_failure():
    service = EmailService(smtp_config=_smtp_config())
    with patch.object(service, "render_html", side_effect=RuntimeError("bad template")):
        ok = service.send_template_email(
            to_email="to@example.com",
            subject="s",
            template_name="anything.html",
            context={},
        )
        assert ok is False


def test_send_email_skips_login_when_no_credentials():
    cfg = SMTPConfig(
        host="smtp.example.com",
        port=587,
        user=None,
        password=None,
        from_email="no-reply@example.com",
        use_starttls=False,
    )

    service = EmailService(smtp_config=cfg)
    with patch("app.core.mail.smtplib.SMTP") as smtp:
        server = MagicMock()
        smtp.return_value.__enter__.return_value = server

        ok = service.send_email(
            to_email="to@example.com",
            subject="Test Subject",
            html_body="<p>Hello</p>",
        )
        assert ok is True
        server.starttls.assert_not_called()
        server.login.assert_not_called()
