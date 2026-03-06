import pytest
import resend
from unittest.mock import patch, MagicMock
from app.core.mail import email_service
from app.models.email_log import EmailStatus

@pytest.mark.asyncio
async def test_create_and_verify_token():
    email = "test@example.com"
    salt = "test-salt"
    token = email_service.create_token(email, salt)
    assert token is not None
    
    decoded = email_service.verify_token(token, salt)
    assert decoded == email

    # Test bad token
    assert email_service.verify_token("bad-token", salt) is None

def test_send_email_background_success():
    """Test successful email sending with mock Resend"""
    # Patch config on the instance
    email_service.config = MagicMock(api_key="re_123", sender="test@test.com")
    
    with patch("app.core.mail.resend.Emails.send") as mock_send, \
         patch.object(email_service, "_log_attempt") as mock_log, \
         patch.object(email_service, "render_template", return_value="<html></html>"):
        
        mock_send.return_value = {"id": "re_mock_id"}
        
        email_service.send_email_background(
            "user@test.com", "Subject", "test.html", {}
        )
        
        mock_send.assert_called_once()
        mock_log.assert_called_with(
            "user@test.com", "Subject", "test.html", EmailStatus.SENT, provider_id="re_mock_id"
        )

def test_send_email_retry_on_rate_limit_error():
    """429 应重试（最多 3 次）"""
    email_service.config = MagicMock(api_key="re_123", sender="test@test.com")

    err = resend.exceptions.RateLimitError("Too many requests", "rate_limit_exceeded", 429)
    with patch("app.core.mail.resend.Emails.send", side_effect=err) as mock_send, \
         patch.object(email_service, "_log_attempt") as mock_log, \
         patch.object(email_service, "render_template", return_value="<html></html>"):

        email_service.send_email_background(
           "user@test.com", "Subject", "test.html", {}
        )

        assert mock_send.call_count == 3
        mock_log.assert_called_with(
            "user@test.com", "Subject", "test.html", EmailStatus.FAILED, error_message="Too many requests"
        )


def test_send_email_no_retry_on_validation_error():
    """422/ValidationError 不应重试"""
    email_service.config = MagicMock(api_key="re_123", sender="test@test.com")

    err = resend.exceptions.ValidationError("Invalid payload", "validation_error", 422)
    with patch("app.core.mail.resend.Emails.send", side_effect=err) as mock_send, \
         patch.object(email_service, "_log_attempt") as mock_log, \
         patch.object(email_service, "render_template", return_value="<html></html>"):

        email_service.send_email_background(
            "user@test.com", "Subject", "test.html", {}
        )

        assert mock_send.call_count == 1
        mock_log.assert_called_with(
            "user@test.com", "Subject", "test.html", EmailStatus.FAILED, error_message="Invalid payload"
        )
