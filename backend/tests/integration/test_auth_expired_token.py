import pytest
from httpx import AsyncClient
from unittest.mock import MagicMock, patch


def build_supabase_mock():
    mock = MagicMock()
    mock.table.return_value = mock
    mock.insert.return_value = mock
    mock.execute.return_value = MagicMock(data=[])
    return mock


@pytest.mark.asyncio
async def test_expired_token_rejected(client: AsyncClient, expired_token: str):
    """过期令牌应返回 401"""
    mock = build_supabase_mock()
    with patch("app.lib.api_client.supabase", mock), \
         patch("app.api.v1.manuscripts.supabase", mock):
        response = await client.post(
            "/api/v1/manuscripts",
            json={
                "title": "Expired Token Manuscript",
                "abstract": "Expired auth header",
                "author_id": "00000000-0000-0000-0000-000000000000"
            },
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert response.status_code == 401
