from unittest.mock import MagicMock, patch

from app.core.config import SMTPConfig
from app.core.mail import EmailService
from app.models.email_log import EmailLogCreate


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


def test_send_inline_email_deduplicates_template_tag_for_resend():
    service = EmailService(
        smtp_config=None,
        resend_config=None,
        supabase_client=None,
    )
    service.config = type(
        "LegacyResendConfig",
        (),
        {
            "api_key": "re_test_xxx",
            "sender": "ScholarFlow <no-reply@example.com>",
        },
    )()

    with (
        patch.object(service, "_send_resend_message", return_value={"id": "email_123"}) as send_mock,
        patch.object(service, "_log_attempt"),
    ):
        result = service.send_inline_email(
            to_email="reviewer@example.com",
            template_key="reviewer_invitation_standard",
            subject_template="Review {{ manuscript_title }}",
            body_html_template="<p>Hello {{ reviewer_name }}</p>",
            context={"manuscript_title": "Test Manuscript", "reviewer_name": "Reviewer X"},
            tags=[
                {"name": "scene", "value": "reviewer_assignment"},
                {"name": "template", "value": "reviewer_invitation_standard"},
                {"name": "assignment_id", "value": "assignment_1"},
            ],
        )

    assert result["status"] == "sent"
    send_kwargs = send_mock.call_args.kwargs
    assert send_kwargs["tags"] == [
        {"name": "scene", "value": "reviewer_assignment"},
        {"name": "assignment_id", "value": "assignment_1"},
        {"name": "template", "value": "reviewer_invitation_standard"},
    ]


def test_derive_plain_text_from_html_preserves_link_targets():
    service = EmailService(
        smtp_config=None,
        resend_config=None,
        supabase_client=None,
    )

    text = service.derive_plain_text_from_html(
        '<p>Hello <a href="https://example.com/review">Review Link</a></p><p>Thanks</p>'
    )

    assert text == "Hello Review Link (https://example.com/review)\n\nThanks"


def test_email_log_create_supports_delivery_envelope_fields():
    log = EmailLogCreate(
        recipient="lead@example.com",
        subject="Invoice Ready",
        template_name="invoice_email",
        to_recipients=["lead@example.com", "co@example.com"],
        cc_recipients=["office@example.com"],
        bcc_recipients=["archive@example.com"],
        reply_to_recipients=["office@example.com"],
        delivery_mode="manual",
        provider="resend",
        communication_status="external_sent",
        attachment_count=1,
        attachment_manifest=[
            {
                "filename": "invoice.pdf",
                "content_type": "application/pdf",
            }
        ],
    )

    assert log.to_recipients == ["lead@example.com", "co@example.com"]
    assert log.cc_recipients == ["office@example.com"]
    assert log.bcc_recipients == ["archive@example.com"]
    assert log.reply_to_recipients == ["office@example.com"]
    assert log.delivery_mode == "manual"
    assert log.provider == "resend"
    assert log.communication_status == "external_sent"
    assert log.attachment_count == 1
    assert log.attachment_manifest == [
        {
            "filename": "invoice.pdf",
            "content_type": "application/pdf",
        }
    ]


def test_send_email_supports_cc_bcc_reply_to_and_attachments_for_smtp():
    service = EmailService(smtp_config=_smtp_config())
    with patch("app.core.mail.smtplib.SMTP") as smtp:
        server = MagicMock()
        smtp.return_value.__enter__.return_value = server

        ok = service.send_email(
            to_emails=["to@example.com", "second@example.com"],
            cc_emails=["cc@example.com"],
            bcc_emails=["bcc@example.com"],
            reply_to_emails=["reply@example.com"],
            subject="Invoice Attached",
            html_body="<p>Hello</p>",
            text_body="Hello",
            attachments=[
                {
                    "filename": "invoice.pdf",
                    "content": b"%PDF-1.4 test",
                    "content_type": "application/pdf",
                }
            ],
        )

    assert ok is True
    sendmail_args = server.sendmail.call_args.args
    assert sendmail_args[1] == [
        "to@example.com",
        "second@example.com",
        "cc@example.com",
        "bcc@example.com",
    ]
    raw_message = sendmail_args[2]
    assert "Cc: cc@example.com" in raw_message
    assert "Reply-To: reply@example.com" in raw_message
    assert 'filename="invoice.pdf"' in raw_message


def test_send_rendered_email_passes_envelope_and_logs_delivery_metadata():
    supabase = MagicMock()
    supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()
    service = EmailService(
        smtp_config=None,
        resend_config=None,
        supabase_client=supabase,
    )
    service.config = type(
        "LegacyResendConfig",
        (),
        {
            "api_key": "re_test_xxx",
            "sender": "ScholarFlow <no-reply@example.com>",
        },
    )()

    with patch.object(service, "_send_resend_message", return_value={"id": "email_123"}) as send_mock:
        result = service.send_rendered_email(
            to_emails=["lead@example.com", "co@example.com"],
            cc_emails=["office@example.com"],
            bcc_emails=["archive@example.com"],
            reply_to_emails=["office@example.com"],
            template_key="invoice_email",
            subject="Invoice Attached",
            html_body="<p>Please find attached</p>",
            attachments=[
                {
                    "filename": "invoice.pdf",
                    "content": b"%PDF-1.4 test",
                    "content_type": "application/pdf",
                }
            ],
            audit_context={
                "scene": "invoice",
                "event_type": "invoice_send",
                "actor_user_id": "11111111-1111-1111-1111-111111111111",
                "delivery_mode": "manual",
                "communication_status": "system_sent",
            },
        )

    assert result["status"] == "sent"
    send_kwargs = send_mock.call_args.kwargs
    assert send_kwargs["to_emails"] == ["lead@example.com", "co@example.com"]
    assert send_kwargs["cc_emails"] == ["office@example.com"]
    assert send_kwargs["bcc_emails"] == ["archive@example.com"]
    assert send_kwargs["reply_to_emails"] == ["office@example.com"]
    assert send_kwargs["attachments"][0]["filename"] == "invoice.pdf"

    logged_payload = supabase.table.return_value.insert.call_args.args[0]
    assert logged_payload["recipient"] == "lead@example.com"
    assert logged_payload["to_recipients"] == ["lead@example.com", "co@example.com"]
    assert logged_payload["cc_recipients"] == ["office@example.com"]
    assert logged_payload["bcc_recipients"] == ["archive@example.com"]
    assert logged_payload["reply_to_recipients"] == ["office@example.com"]
    assert logged_payload["provider"] == "resend"
    assert logged_payload["delivery_mode"] == "manual"
    assert logged_payload["communication_status"] == "system_sent"
    assert logged_payload["attachment_count"] == 1
    assert logged_payload["attachment_manifest"] == [
        {
            "filename": "invoice.pdf",
            "content_type": "application/pdf",
        }
    ]
