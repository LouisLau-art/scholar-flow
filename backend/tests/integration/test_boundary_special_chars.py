import pytest
from httpx import AsyncClient
from unittest.mock import MagicMock, patch

# === 边界条件: 特殊字符 ===

def _mock_supabase_with_data(data=None):
    mock = MagicMock()
    mock.table.return_value = mock
    mock.select.return_value = mock
    mock.order.return_value = mock
    mock.eq.return_value = mock
    mock.or_.return_value = mock
    mock.single.return_value = mock
    mock.insert.return_value = mock
    mock.update.return_value = mock
    response = MagicMock()
    response.data = data or []
    response.error = None
    mock.execute.return_value = response
    return mock

@pytest.mark.asyncio
async def test_create_manuscript_with_special_chars(client: AsyncClient, auth_token: str):
    """验证包含特殊字符的标题和摘要可正常创建"""
    mock_data = [{
        "id": "special-1",
        "title": "AI & ML: 研究@2026 #1",
        "abstract": "包含特殊符号 !@#$%^&*()_+ 以及中文标点。并且这段摘要足够长以通过校验。",
        "author_id": "00000000-0000-0000-0000-000000000000",
        "status": "submitted",
        "created_at": "2026-01-28T00:00:00.000000+00:00",
        "updated_at": "2026-01-28T00:00:00.000000+00:00",
    }]
    mock = _mock_supabase_with_data(mock_data)

    with patch("app.lib.api_client.supabase", mock), \
         patch("app.api.v1.manuscripts.supabase", mock):
        response = await client.post(
            "/api/v1/manuscripts",
            json={
                "title": "AI & ML: 研究@2026 #1",
                "abstract": "包含特殊符号 !@#$%^&*()_+ 以及中文标点。并且这段摘要足够长以通过校验。",
                "author_id": "00000000-0000-0000-0000-000000000000",
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        assert response.json()["success"] is True
