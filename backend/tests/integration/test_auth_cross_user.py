import pytest
from httpx import AsyncClient
from unittest.mock import MagicMock, patch


def build_supabase_mock(data):
    mock = MagicMock()
    mock.table.return_value = mock
    mock.insert.return_value = mock
    mock.execute.return_value = MagicMock(data=data)
    return mock


@pytest.mark.asyncio
async def test_cross_user_author_id_ignored(client: AsyncClient, auth_token: str):
    """创建稿件时应强制使用当前用户身份"""
    token_user_id = "00000000-0000-0000-0000-000000000000"
    provided_author_id = "11111111-1111-1111-1111-111111111111"
    mock_data = [{
        "id": "22222222-2222-2222-2222-222222222222",
        "title": "Auth Bound Manuscript",
        "abstract": "This is a sufficiently long abstract for validation rules.",
        "author_id": token_user_id,
        "status": "submitted"
    }]
    mock = build_supabase_mock(mock_data)

    with patch("app.lib.api_client.supabase", mock), \
         patch("app.api.v1.manuscripts.supabase", mock):
        response = await client.post(
            "/api/v1/manuscripts",
            json={
                "title": "Auth Bound Manuscript",
                "abstract": "This is a sufficiently long abstract for validation rules.",
                "author_id": provided_author_id
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert result["data"]["author_id"] == token_user_id

        insert_payload = mock.insert.call_args[0][0]
        assert insert_payload["author_id"] == token_user_id
        assert insert_payload["author_id"] != provided_author_id
