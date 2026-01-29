import pytest
import asyncio
from httpx import AsyncClient
from unittest.mock import MagicMock, patch

# === 并发请求: 审稿分配 ===

def _mock_supabase_with_side_effect(responses):
    mock = MagicMock()
    mock.table.return_value = mock
    mock.select.return_value = mock
    mock.eq.return_value = mock
    mock.single.return_value = mock
    mock.insert.return_value = mock
    mock.execute.side_effect = responses
    return mock

@pytest.mark.asyncio
async def test_concurrent_reviewer_assignments(client: AsyncClient):
    """验证并发分配审稿人不会导致异常"""
    responses = []
    # 每个请求需要 2 次 execute: select -> insert
    for idx in range(5):
        select_resp = MagicMock()
        select_resp.data = {"author_id": "author-1"}
        insert_resp = MagicMock()
        insert_resp.data = [{"id": f"assign-{idx}", "status": "pending"}]
        responses.extend([select_resp, insert_resp])

    mock = _mock_supabase_with_side_effect(responses)

    with patch("app.lib.api_client.supabase", mock), \
         patch("app.api.v1.reviews.supabase", mock):
        async def assign(i: int):
            return await client.post(
                "/api/v1/reviews/assign",
                json={
                    "manuscript_id": "00000000-0000-0000-0000-000000000000",
                    "reviewer_id": f"00000000-0000-0000-0000-00000000000{i}",
                },
            )

        results = await asyncio.gather(*[assign(i) for i in range(5)])

        assert all(r.status_code == 200 for r in results)
        assert all(r.json().get("success") is True for r in results)
