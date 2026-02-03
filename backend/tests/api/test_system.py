import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


@pytest.fixture
def mock_supabase():
    with patch("app.api.v1.endpoints.system.supabase") as mock_client:
        yield mock_client


@pytest.mark.unit
def test_submit_feedback_success(mock_supabase):
    """
    Test successful feedback submission.
    """
    # Mock the database response
    mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
        {"id": "123-uuid", "status": "new"}
    ]

    payload = {
        "description": "The button is broken on staging.",
        "severity": "medium",
        "url": "http://localhost:3000/dashboard",
    }

    response = client.post("/api/v1/system/feedback", json=payload)

    assert response.status_code == 201
    assert response.json()["status"] == "received"

    # Verify DB call
    mock_supabase.table.assert_called_with("uat_feedback")
    mock_supabase.table().insert.assert_called()


@pytest.mark.unit
def test_submit_feedback_validation_error():
    """
    Test validation failure (description too short).
    """
    payload = {
        "description": "Bad",  # Too short (<5)
        "severity": "medium",
        "url": "http://localhost:3000",
    }

    response = client.post("/api/v1/system/feedback", json=payload)

    assert response.status_code == 422
