import pytest
from httpx import AsyncClient
from unittest.mock import patch

# === 错误处理测试 ===

@pytest.mark.asyncio
async def test_not_found_route(client: AsyncClient):
    """验证 404 路由"""
    response = await client.get("/api/v1/does-not-exist")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_upload_internal_error(client: AsyncClient):
    """验证上传流程内部异常返回 500"""
    with patch("app.api.v1.manuscripts.extract_text_and_layout_from_pdf", return_value=("text", [])), \
         patch("app.api.v1.manuscripts.parse_manuscript_metadata", side_effect=Exception("boom")), \
         patch("app.api.v1.manuscripts.plagiarism_check_worker", return_value=None):
        response = await client.post(
            "/api/v1/manuscripts/upload",
            files={"file": ("test.pdf", b"%PDF-1.4 test", "application/pdf")},
        )
        assert response.status_code == 500
        payload = response.json()
        assert payload["success"] is False
        assert "boom" in payload["message"]
