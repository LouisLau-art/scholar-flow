import pytest
from httpx import AsyncClient
from unittest.mock import patch, MagicMock
import uuid
import os
from jose import jwt

# === 稿件业务核心测试 (真实行为模拟版) ===

def get_full_mock(data_to_return):
    mock = MagicMock()
    # 模拟链式调用返回自己
    mock.table.return_value = mock
    mock.select.return_value = mock
    mock.order.return_value = mock
    mock.eq.return_value = mock
    mock.or_.return_value = mock
    mock.single.return_value = mock
    mock.insert.return_value = mock
    mock.update.return_value = mock

    # 模拟 execute() 返回一个带 data 属性的对象
    mock_response = MagicMock()
    mock_response.data = data_to_return
    mock.execute.return_value = mock_response
    return mock

def generate_test_token(user_id: str = "00000000-0000-0000-0000-000000000000"):
    """生成测试用的 JWT token"""
    secret = os.environ.get("SUPABASE_JWT_SECRET", "mock-secret-replace-later")
    payload = {
        "sub": user_id,
        "email": "test@example.com",
        "aud": "authenticated"
    }
    return jwt.encode(payload, secret, algorithm="HS256")

@pytest.mark.asyncio
async def test_get_manuscripts_empty(client: AsyncClient):
    """验证列表接口返回成功"""
    mock = get_full_mock([])
    with patch("app.lib.api_client.supabase", mock), \
         patch("app.api.v1.manuscripts.supabase", mock):
        response = await client.get("/api/v1/manuscripts")
        assert response.status_code == 200
        assert response.json()["success"] is True

@pytest.mark.asyncio
async def test_search_manuscripts(client: AsyncClient):
    """验证搜索接口的返回结构"""
    mock = get_full_mock([{"id": "1", "title": "Test Paper"}])
    with patch("app.lib.api_client.supabase", mock), \
         patch("app.api.v1.manuscripts.supabase", mock):
        response = await client.get("/api/v1/manuscripts/search?q=AI")
        assert response.status_code == 200
        assert "results" in response.json()
        assert len(response.json()["results"]) > 0

@pytest.mark.asyncio
async def test_create_manuscript_success(client: AsyncClient):
    """验证创建稿件接口成功"""
    manuscript_id = str(uuid.uuid4())
    mock_data = {
        "id": manuscript_id,
        "title": "Test Manuscript",
        "abstract": "This is a sufficiently long abstract content for validation.",
        "dataset_url": "https://example.com/dataset",
        "source_code_url": "https://github.com/example/repo",
        "author_id": "00000000-0000-0000-0000-000000000000",
        "status": "submitted",
        "created_at": "2026-01-28T00:00:00.000000+00:00",
        "updated_at": "2026-01-28T00:00:00.000000+00:00"
    }
    mock = get_full_mock([mock_data])

    # Generate valid JWT token
    mock_token = generate_test_token()

    with patch("app.lib.api_client.supabase", mock), \
         patch("app.api.v1.manuscripts.supabase", mock):
        response = await client.post(
            "/api/v1/manuscripts",
            json={
                "title": "Test Manuscript",
                "abstract": "This is a sufficiently long abstract content for validation.",
                "dataset_url": "https://example.com/dataset",
                "source_code_url": "https://github.com/example/repo",
                "author_id": "00000000-0000-0000-0000-000000000000"
            },
            headers={"Authorization": f"Bearer {mock_token}"}
        )
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert result["data"]["title"] == "Test Manuscript"
        assert result["data"]["status"] == "submitted"
        assert result["data"]["dataset_url"] == "https://example.com/dataset"
        assert result["data"]["source_code_url"] == "https://github.com/example/repo"

        insert_payload = mock.insert.call_args[0][0]
        assert insert_payload["dataset_url"] == "https://example.com/dataset"
        assert insert_payload["source_code_url"] == "https://github.com/example/repo"

@pytest.mark.asyncio
async def test_create_manuscript_invalid_data(client: AsyncClient):
    """验证创建稿件接口的参数验证"""
    mock = get_full_mock([])

    # Generate valid JWT token
    mock_token = generate_test_token()

    with patch("app.lib.api_client.supabase", mock), \
         patch("app.api.v1.manuscripts.supabase", mock):
        # 测试缺少必填字段
        response = await client.post(
            "/api/v1/manuscripts",
            json={
                "title": "",  # 空标题
                "abstract": "",
                "author_id": "00000000-0000-0000-0000-000000000000"
            },
            headers={"Authorization": f"Bearer {mock_token}"}
        )
        # FastAPI 应该返回 422 验证错误
        assert response.status_code == 422

@pytest.mark.asyncio
async def test_create_manuscript_ignores_cross_user_author_id(client: AsyncClient):
    """验证创建稿件时强制使用当前用户身份"""
    token_user_id = "11111111-1111-1111-1111-111111111111"
    provided_author_id = "22222222-2222-2222-2222-222222222222"
    manuscript_id = str(uuid.uuid4())
    mock_data = {
        "id": manuscript_id,
        "title": "Auth Bound Manuscript",
        "abstract": "This is a sufficiently long abstract content for validation.",
        "author_id": token_user_id,
        "status": "submitted",
        "created_at": "2026-01-28T00:00:00.000000+00:00",
        "updated_at": "2026-01-28T00:00:00.000000+00:00"
    }
    mock = get_full_mock([mock_data])

    # Generate valid JWT token for token_user_id
    mock_token = generate_test_token(user_id=token_user_id)

    with patch("app.lib.api_client.supabase", mock), \
         patch("app.api.v1.manuscripts.supabase", mock):
        response = await client.post(
            "/api/v1/manuscripts",
            json={
                "title": "Auth Bound Manuscript",
                "abstract": "This is a sufficiently long abstract content for validation.",
                "author_id": provided_author_id
            },
            headers={"Authorization": f"Bearer {mock_token}"}
        )
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert result["data"]["author_id"] == token_user_id
        assert result["data"]["author_id"] != provided_author_id

        # 验证插入数据使用了 token 用户 ID
        insert_payload = mock.insert.call_args[0][0]
        assert insert_payload["author_id"] == token_user_id
        assert insert_payload["author_id"] != provided_author_id

@pytest.mark.asyncio
async def test_get_manuscripts_list(client: AsyncClient):
    """验证获取稿件列表接口"""
    mock_data = [
        {"id": str(uuid.uuid4()), "title": "Paper 1", "status": "submitted"},
        {"id": str(uuid.uuid4()), "title": "Paper 2", "status": "under_review"}
    ]
    mock = get_full_mock(mock_data)
    with patch("app.lib.api_client.supabase", mock), \
         patch("app.api.v1.manuscripts.supabase", mock):
        response = await client.get("/api/v1/manuscripts")
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert len(result["data"]) == 2

@pytest.mark.asyncio
async def test_route_path_matching(client: AsyncClient):
    """验证路由路径匹配（GET 和 POST 都能正常工作）"""
    mock = get_full_mock([])

    # Generate valid JWT token
    mock_token = generate_test_token()

    # 测试 GET 路由
    with patch("app.lib.api_client.supabase", mock), \
         patch("app.api.v1.manuscripts.supabase", mock):
        get_response = await client.get("/api/v1/manuscripts")
        assert get_response.status_code == 200

    # 测试 POST 路由（使用相同的路径）
    mock_data = [{"id": str(uuid.uuid4()), "title": "Test"}]
    mock = get_full_mock(mock_data)
    with patch("app.lib.api_client.supabase", mock), \
         patch("app.api.v1.manuscripts.supabase", mock):
        post_response = await client.post(
            "/api/v1/manuscripts",
            json={
                "title": "Valid Title",
                "abstract": "This is a sufficiently long abstract content for validation.",
                "author_id": "00000000-0000-0000-0000-000000000000"
            },
            headers={"Authorization": f"Bearer {mock_token}"}
        )
        assert post_response.status_code == 200


@pytest.mark.asyncio
async def test_upload_rejects_non_pdf(client: AsyncClient):
    """验证上传接口拒绝非 PDF 文件"""
    files = {"file": ("note.txt", b"hello", "text/plain")}
    response = await client.post("/api/v1/manuscripts/upload", files=files)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_quality_check_endpoint_calls_service(client: AsyncClient):
    """验证质检接口调用 service 并返回结果"""
    from uuid import uuid4

    manuscript_id = uuid4()
    expected = {"manuscript_id": str(manuscript_id), "passed": True}

    async def fake_quality_check(_manuscript_id, passed, _kpi_owner_id):
        return {"manuscript_id": str(_manuscript_id), "passed": passed}

    with patch("app.api.v1.manuscripts.process_quality_check", fake_quality_check):
        response = await client.post(
            f"/api/v1/manuscripts/{manuscript_id}/quality-check",
            json={
                "passed": True,
                "kpi_owner_id": "00000000-0000-0000-0000-000000000000",
            },
        )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["data"] == expected
