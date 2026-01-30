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

