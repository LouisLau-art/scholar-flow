import pytest
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

def test_send_email_retry_failure():
    """Test retry logic on failure"""
    email_service.config = MagicMock(api_key="re_123", sender="test@test.com")
    
    # We mock wait_exponential to be 0 to speed up test
    with patch("app.core.mail.resend.Emails.send", side_effect=Exception("Network Error")) as mock_send, \
         patch.object(email_service, "_log_attempt") as mock_log, \
         patch.object(email_service, "render_template", return_value="<html></html>"), \
         patch("app.core.mail.wait_exponential", return_value=0): # This might not work with decorator.
         # Decorator is evaluated at import time. We can't easily patch the wait time dynamically without deeper hacking.
         # But tenacity retry is fast enough for 3 attempts if we don't block.
         # Actually wait_exponential defaults min=2, so it will wait 2s, 4s. Test will take 6s. Acceptable.
         
         email_service.send_email_background(
            "user@test.com", "Subject", "test.html", {}
         )
         
         # Should be called 3 times due to retry
         assert mock_send.call_count == 3
         mock_log.assert_called_with(
             "user@test.com", "Subject", "test.html", EmailStatus.FAILED, error_message="Network Error"
         )
