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
async def test_abstract_max_length_exceeded(client: AsyncClient, auth_token: str):
    """摘要超过最大长度应返回 422"""
    mock = build_supabase_mock([])
    with patch("app.lib.api_client.supabase", mock), \
         patch("app.api.v1.manuscripts.supabase", mock):
        response = await client.post(
            "/api/v1/manuscripts",
            json={
                "title": "Valid title",
                "abstract": "A" * 5001,
                "author_id": "00000000-0000-0000-0000-000000000000"
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_abstract_min_length_boundary(client: AsyncClient, auth_token: str):
    """摘要最小长度应允许通过"""
    mock_data = [{
        "id": "22222222-2222-2222-2222-222222222222",
        "title": "Valid title",
        "abstract": "This is a sufficiently long abstract for validation rules.",
        "author_id": "00000000-0000-0000-0000-000000000000",
        "status": "pre_check"
    }]
    mock = build_supabase_mock(mock_data)
    with patch("app.lib.api_client.supabase", mock), \
         patch("app.api.v1.manuscripts.supabase", mock):
        response = await client.post(
            "/api/v1/manuscripts",
            json={
                "title": "Valid title",
                "abstract": "This is a sufficiently long abstract for validation rules.",
                "author_id": "00000000-0000-0000-0000-000000000000"
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
