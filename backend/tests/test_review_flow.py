import pytest
from httpx import AsyncClient
from unittest.mock import patch, MagicMock
from uuid import uuid4

def get_supabase_mock(return_data):
    mock = MagicMock()
    mock.table.return_value = mock
    mock.select.return_value = mock
    mock.eq.return_value = mock
    mock.single.return_value = mock
    mock.insert.return_value = mock
    mock.update.return_value = mock
    
    mock_res = MagicMock()
    mock_res.data = return_data
    mock.execute.return_value = mock_res
    return mock

@pytest.mark.asyncio
async def test_assign_reviewer_conflict(client: AsyncClient, auth_token: str, monkeypatch):
    """验证作者不能被分配为自己稿件的审稿人"""
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")
    author_id = uuid4()
    # 模拟返回的稿件作者正是我们要分配的审稿人
    mock = get_supabase_mock({"author_id": author_id})
    
    with patch("app.api.v1.reviews.supabase", mock):
        payload = {
            "manuscript_id": str(uuid4()),
            "reviewer_id": str(author_id)
        }
        response = await client.post(
            "/api/v1/reviews/assign",
            json=payload,
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 400
        assert "作者不能评审自己的稿件" in response.json()["detail"]

@pytest.mark.asyncio
async def test_submit_review_success(client: AsyncClient):
    """验证评审提交逻辑"""
    mock = get_supabase_mock([{"id": "test-assignment"}])
    with patch("app.api.v1.reviews.supabase", mock):
        payload = {
            "assignment_id": str(uuid4()),
            "scores": {"novelty": 5, "rigor": 4},
            "comments": "Great work!"
        }
        response = await client.post("/api/v1/reviews/submit", json=payload)
        assert response.status_code == 200
        assert response.json()["success"] is True
