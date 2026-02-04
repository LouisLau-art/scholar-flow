import pytest
import asyncio
from httpx import AsyncClient
from unittest.mock import MagicMock, patch

# === 并发请求: 稿件提交 ===

def _mock_supabase_with_side_effect(responses):
    mock = MagicMock()
    mock.table.return_value = mock
    mock.select.return_value = mock
    mock.order.return_value = mock
    mock.eq.return_value = mock
    mock.or_.return_value = mock
    mock.single.return_value = mock
    mock.insert.return_value = mock
    mock.update.return_value = mock
    mock.execute.side_effect = responses
    return mock

@pytest.mark.asyncio
async def test_concurrent_manuscript_submissions(client: AsyncClient, auth_token: str):
    """验证并发投稿不会导致异常"""
    headers = {"Authorization": f"Bearer {auth_token}"}

    responses = []
    for idx in range(5):
        response = MagicMock()
        response.data = [{"id": f"m-{idx}", "title": f"Paper {idx}", "status": "pre_check"}]
        responses.append(response)

    mock = _mock_supabase_with_side_effect(responses)

    with patch("app.lib.api_client.supabase", mock), \
         patch("app.api.v1.manuscripts.supabase", mock):
        async def submit(i: int):
            return await client.post(
                "/api/v1/manuscripts",
                json={
                    "title": f"Paper {i}",
                    "abstract": "This is a sufficiently long abstract for concurrent submission testing.",
                    "author_id": "00000000-0000-0000-0000-000000000000",
                },
                headers=headers,
            )

        results = await asyncio.gather(*[submit(i) for i in range(5)])

        assert all(r.status_code == 200 for r in results)
        assert all(r.json().get("success") is True for r in results)
