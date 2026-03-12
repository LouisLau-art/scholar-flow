import asyncio
import os
from pathlib import Path
import re
import uuid
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient
from jose import jwt

# === 稿件业务核心测试 (真实行为模拟版) ===

def get_full_mock(data_to_return):
    mock = MagicMock()
    # 模拟链式调用返回自己
    mock.table.return_value = mock
    mock.select.return_value = mock
    mock.order.return_value = mock
    mock.eq.return_value = mock
    mock.limit.return_value = mock
    mock.or_.return_value = mock
    mock.single.return_value = mock
    mock.insert.return_value = mock
    mock.update.return_value = mock
    mock.upsert.return_value = mock
    mock.delete.return_value = mock

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


def required_submission_files(user_id: str):
    return {
        "file_path": f"{user_id}/paper.pdf",
        "manuscript_word_path": f"{user_id}/word-manuscripts/paper.docx",
        "manuscript_word_filename": "paper.docx",
        "manuscript_word_content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "cover_letter_path": f"{user_id}/cover-letters/cover-letter.pdf",
        "cover_letter_filename": "cover-letter.pdf",
        "cover_letter_content_type": "application/pdf",
    }


def required_author_contacts():
    return [
        {
            "name": "Alice Author",
            "email": "alice.author@example.org",
            "affiliation": "Example University",
            "city": "Wuhan",
            "country_or_region": "China",
            "is_corresponding": True,
        },
        {
            "name": "Bob Author",
            "email": "bob.author@example.org",
            "affiliation": "Example Institute",
            "city": "Beijing",
            "country_or_region": "China",
            "is_corresponding": False,
        },
    ]


def required_zip_submission_files(user_id: str):
    return {
        "file_path": f"{user_id}/paper.pdf",
        "source_archive_path": f"{user_id}/source-archives/paper-source.zip",
        "source_archive_filename": "paper-source.zip",
        "source_archive_content_type": "application/zip",
        "cover_letter_path": f"{user_id}/cover-letters/cover-letter.pdf",
        "cover_letter_filename": "cover-letter.pdf",
        "cover_letter_content_type": "application/pdf",
    }


def test_manuscript_files_migration_allows_source_archive_file_type():
    """验证云端 migration 已显式放行 ZIP 源文件 taxonomy。"""
    migrations_dir = Path(__file__).resolve().parents[2] / "supabase" / "migrations"
    matching_migrations = []

    for migration_path in sorted(migrations_dir.glob("*.sql")):
        sql = migration_path.read_text(encoding="utf-8")
        if "manuscript_files_file_type_check" in sql and "source_archive" in sql:
            matching_migrations.append(migration_path.name)

    assert matching_migrations, "缺少允许 source_archive 的 manuscript_files 约束迁移"

@pytest.mark.asyncio
async def test_get_manuscripts_empty(client: AsyncClient, auth_token: str):
    """验证列表接口返回成功"""
    mock = get_full_mock([])
    with patch("app.lib.api_client.supabase", mock), \
         patch("app.api.v1.manuscripts.supabase", mock):
        response = await client.get("/api/v1/manuscripts", headers={"Authorization": f"Bearer {auth_token}"})
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
        "submission_email": "corresponding@example.org",
        "authors": ["Alice Author", "Bob Author"],
        "author_contacts": required_author_contacts(),
        "dataset_url": "https://example.com/dataset",
        "source_code_url": "https://github.com/example/repo",
        "author_id": "00000000-0000-0000-0000-000000000000",
        "status": "pre_check",
        "created_at": "2026-01-28T00:00:00.000000+00:00",
        "updated_at": "2026-01-28T00:00:00.000000+00:00"
    }
    mock = get_full_mock([mock_data])
    admin_mock = get_full_mock([{"id": str(uuid.uuid4())}])

    # Generate valid JWT token
    mock_token = generate_test_token()

    with patch("app.lib.api_client.supabase", mock), \
         patch("app.api.v1.manuscripts.supabase", mock), \
         patch("app.api.v1.manuscripts.supabase_admin", admin_mock):
        response = await client.post(
            "/api/v1/manuscripts",
            json={
                "title": "Test Manuscript",
                "abstract": "This is a sufficiently long abstract content for validation.",
                "submission_email": "corresponding@example.org",
                "author_contacts": required_author_contacts(),
                "dataset_url": "https://example.com/dataset",
                "source_code_url": "https://github.com/example/repo",
                "author_id": "00000000-0000-0000-0000-000000000000",
                **required_submission_files("00000000-0000-0000-0000-000000000000"),
            },
            headers={"Authorization": f"Bearer {mock_token}"}
        )
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert result["data"]["title"] == "Test Manuscript"
        assert result["data"]["status"] == "pre_check"
        assert result["data"]["dataset_url"] == "https://example.com/dataset"
        assert result["data"]["source_code_url"] == "https://github.com/example/repo"
        assert result["data"]["submission_email"] == "corresponding@example.org"
        assert result["data"]["authors"] == ["Alice Author", "Bob Author"]

        insert_payload = mock.insert.call_args[0][0]
        assert insert_payload["dataset_url"] == "https://example.com/dataset"
        assert insert_payload["source_code_url"] == "https://github.com/example/repo"
        assert insert_payload["submission_email"] == "corresponding@example.org"
        assert insert_payload["authors"] == ["Alice Author", "Bob Author"]
        assert insert_payload["author_contacts"][0]["is_corresponding"] is True
        assert insert_payload["initial_submitted_at"] == insert_payload["created_at"]


@pytest.mark.asyncio
async def test_create_manuscript_retries_without_initial_submitted_at_when_schema_cache_is_stale(
    client: AsyncClient,
):
    manuscript_id = str(uuid.uuid4())
    mock_data = {
        "id": manuscript_id,
        "title": "Compat Manuscript",
        "abstract": "This is a sufficiently long abstract content for validation.",
        "submission_email": "corresponding@example.org",
        "authors": ["Alice Author", "Bob Author"],
        "author_contacts": required_author_contacts(),
        "author_id": "00000000-0000-0000-0000-000000000000",
        "status": "pre_check",
        "created_at": "2026-01-28T00:00:00.000000+00:00",
        "updated_at": "2026-01-28T00:00:00.000000+00:00",
    }
    mock = get_full_mock([mock_data])
    admin_mock = get_full_mock([{"id": str(uuid.uuid4())}])
    mock_token = generate_test_token()

    stale_schema_error = RuntimeError(
        "Could not find the 'initial_submitted_at' column of 'manuscripts' in the schema cache (PGRST204)"
    )
    successful_insert_response = MagicMock()
    successful_insert_response.data = [mock_data]
    mock.execute.side_effect = [stale_schema_error, successful_insert_response]

    with patch("app.lib.api_client.supabase", mock), \
         patch("app.api.v1.manuscripts.supabase", mock), \
         patch("app.api.v1.manuscripts.supabase_admin", admin_mock):
        response = await client.post(
            "/api/v1/manuscripts",
            json={
                "title": "Compat Manuscript",
                "abstract": "This is a sufficiently long abstract content for validation.",
                "submission_email": "corresponding@example.org",
                "author_contacts": required_author_contacts(),
                "author_id": "00000000-0000-0000-0000-000000000000",
                **required_zip_submission_files("00000000-0000-0000-0000-000000000000"),
            },
            headers={"Authorization": f"Bearer {mock_token}"},
        )

    assert response.status_code == 200
    assert mock.insert.call_count == 2

    first_payload = mock.insert.call_args_list[0].args[0]
    second_payload = mock.insert.call_args_list[1].args[0]
    assert "initial_submitted_at" in first_payload
    assert "initial_submitted_at" not in second_payload


@pytest.mark.asyncio
async def test_create_manuscript_submission_ack_uses_resolved_author_target(client: AsyncClient):
    """投稿确认邮件应统一使用解析后的作者通知目标，而不是回退到登录账号邮箱。"""
    manuscript_id = str(uuid.uuid4())
    mock_data = {
        "id": manuscript_id,
        "title": "Targeted Submission",
        "abstract": "This is a sufficiently long abstract content for validation.",
        "submission_email": "delegate@example.org",
        "authors": ["Alice Author", "Bob Author"],
        "author_contacts": required_author_contacts(),
        "author_id": "00000000-0000-0000-0000-000000000000",
        "status": "pre_check",
        "created_at": "2026-01-28T00:00:00.000000+00:00",
        "updated_at": "2026-01-28T00:00:00.000000+00:00",
    }
    mock = get_full_mock([mock_data])
    admin_mock = get_full_mock([{"id": str(uuid.uuid4())}])
    mock_token = generate_test_token()

    with patch("app.lib.api_client.supabase", mock), \
         patch("app.api.v1.manuscripts.supabase", mock), \
         patch("app.api.v1.manuscripts.supabase_admin", admin_mock), \
         patch(
             "app.api.v1.manuscripts_submission.resolve_author_notification_target",
             return_value={"recipient_email": "corr@example.org", "recipient_name": "Alice Author"},
         ) as resolve_target_mock, \
         patch("app.api.v1.manuscripts_submission.BackgroundTasks.add_task", autospec=True) as add_task_mock:
        response = await client.post(
            "/api/v1/manuscripts",
            json={
                "title": "Targeted Submission",
                "abstract": "This is a sufficiently long abstract content for validation.",
                    "submission_email": "delegate@example.org",
                "author_contacts": required_author_contacts(),
                "author_id": "00000000-0000-0000-0000-000000000000",
                **required_submission_files("00000000-0000-0000-0000-000000000000"),
            },
            headers={"Authorization": f"Bearer {mock_token}"}
        )

    assert response.status_code == 200
    resolve_target_mock.assert_called_once()
    assert add_task_mock.call_count == 1
    _, send_callable = add_task_mock.call_args.args[:2]
    assert callable(send_callable)
    assert add_task_mock.call_args.kwargs["to_email"] == "corr@example.org"
    assert add_task_mock.call_args.kwargs["context"]["recipient_name"] == "Alice Author"


def test_ensure_author_role_membership_appends_author_role():
    from app.api.v1 import manuscripts_submission

    admin_mock = MagicMock()
    admin_mock.table.return_value = admin_mock
    admin_mock.select.return_value = admin_mock
    admin_mock.eq.return_value = admin_mock
    admin_mock.limit.return_value = admin_mock
    admin_mock.update.return_value = admin_mock

    select_resp = MagicMock()
    select_resp.data = [
        {
            "id": "user-1",
            "email": "reviewer@example.com",
            "roles": ["reviewer"],
        }
    ]
    update_resp = MagicMock()
    update_resp.data = [{"id": "user-1"}]
    admin_mock.execute.side_effect = [select_resp, update_resp]

    with patch("app.api.v1.manuscripts.supabase_admin", admin_mock):
        manuscripts_submission._ensure_author_role_membership("user-1", "reviewer@example.com")

    admin_mock.table.assert_any_call("user_profiles")
    admin_mock.update.assert_called_once()
    update_payload = admin_mock.update.call_args[0][0]
    assert update_payload["roles"] == ["reviewer", "author"]


def test_ensure_author_role_membership_inserts_missing_profile():
    from app.api.v1 import manuscripts_submission

    admin_mock = MagicMock()
    admin_mock.table.return_value = admin_mock
    admin_mock.select.return_value = admin_mock
    admin_mock.eq.return_value = admin_mock
    admin_mock.limit.return_value = admin_mock
    admin_mock.insert.return_value = admin_mock

    select_resp = MagicMock()
    select_resp.data = []
    insert_resp = MagicMock()
    insert_resp.data = [{"id": "user-2"}]
    admin_mock.execute.side_effect = [select_resp, insert_resp]

    with patch("app.api.v1.manuscripts.supabase_admin", admin_mock):
        manuscripts_submission._ensure_author_role_membership("user-2", "Reviewer@Example.com")

    admin_mock.insert.assert_called_once()
    insert_payload = admin_mock.insert.call_args[0][0]
    assert insert_payload["id"] == "user-2"
    assert insert_payload["email"] == "reviewer@example.com"
    assert insert_payload["roles"] == ["author"]

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
                "submission_email": "invalid",
                "author_contacts": [],
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
        "submission_email": "corresponding@example.org",
        "authors": ["Alice Author", "Bob Author"],
        "author_contacts": required_author_contacts(),
        "author_id": token_user_id,
        "status": "pre_check",
        "created_at": "2026-01-28T00:00:00.000000+00:00",
        "updated_at": "2026-01-28T00:00:00.000000+00:00"
    }
    mock = get_full_mock([mock_data])
    admin_mock = get_full_mock([{"id": str(uuid.uuid4())}])

    # Generate valid JWT token for token_user_id
    mock_token = generate_test_token(user_id=token_user_id)

    with patch("app.lib.api_client.supabase", mock), \
         patch("app.api.v1.manuscripts.supabase", mock), \
         patch("app.api.v1.manuscripts.supabase_admin", admin_mock):
        response = await client.post(
            "/api/v1/manuscripts",
            json={
                "title": "Auth Bound Manuscript",
                "abstract": "This is a sufficiently long abstract content for validation.",
                "submission_email": "corresponding@example.org",
                "author_contacts": required_author_contacts(),
                "author_id": provided_author_id,
                **required_submission_files(token_user_id),
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
async def test_create_manuscript_with_journal_binding(client: AsyncClient):
    """验证创建稿件时可绑定 journal_id"""
    token_user_id = "11111111-1111-1111-1111-111111111111"
    journal_id = str(uuid.uuid4())
    manuscript_id = str(uuid.uuid4())
    mock_data = {
        "id": manuscript_id,
        "title": "Journal Bound Manuscript",
        "abstract": "This is a sufficiently long abstract content for validation.",
        "author_id": token_user_id,
        "journal_id": journal_id,
        "status": "pre_check",
        "created_at": "2026-01-28T00:00:00.000000+00:00",
        "updated_at": "2026-01-28T00:00:00.000000+00:00"
    }
    mock = get_full_mock([mock_data])
    admin_mock = get_full_mock([{"id": journal_id, "is_active": True}])
    mock_token = generate_test_token(user_id=token_user_id)

    with patch("app.lib.api_client.supabase", mock), \
         patch("app.api.v1.manuscripts.supabase", mock), \
         patch("app.api.v1.manuscripts.supabase_admin", admin_mock):
        response = await client.post(
            "/api/v1/manuscripts",
            json={
                "title": "Journal Bound Manuscript",
                "abstract": "This is a sufficiently long abstract content for validation.",
                "submission_email": "corresponding@example.org",
                "author_contacts": required_author_contacts(),
                "author_id": token_user_id,
                "journal_id": journal_id,
                **required_submission_files(token_user_id),
            },
            headers={"Authorization": f"Bearer {mock_token}"}
        )

    assert response.status_code == 200
    insert_payload = mock.insert.call_args[0][0]
    assert insert_payload["journal_id"] == journal_id


@pytest.mark.asyncio
async def test_create_manuscript_requires_at_least_one_corresponding_author(client: AsyncClient):
    mock = get_full_mock([])
    mock_token = generate_test_token()

    with patch("app.lib.api_client.supabase", mock), \
         patch("app.api.v1.manuscripts.supabase", mock):
        response = await client.post(
            "/api/v1/manuscripts",
            json={
                "title": "Structured Author Manuscript",
                "abstract": "This is a sufficiently long abstract content for validation.",
                "submission_email": "submissions@example.org",
                "author_contacts": [
                    {
                        "name": "Alice Author",
                        "email": "alice.author@example.org",
                        "affiliation": "Example University",
                        "city": "Wuhan",
                        "country_or_region": "China",
                        "is_corresponding": False,
                    },
                    {
                        "name": "Bob Author",
                        "email": "bob.author@example.org",
                        "affiliation": "Example Institute",
                        "city": "Beijing",
                        "country_or_region": "China",
                        "is_corresponding": False,
                    },
                ],
                "author_id": "00000000-0000-0000-0000-000000000000",
                **required_submission_files("00000000-0000-0000-0000-000000000000"),
            },
            headers={"Authorization": f"Bearer {mock_token}"}
        )

        assert response.status_code == 422
        assert "corresponding" in response.text.lower()


@pytest.mark.asyncio
async def test_create_manuscript_allows_multiple_corresponding_authors(client: AsyncClient):
    manuscript_id = str(uuid.uuid4())
    mock_data = {
        "id": manuscript_id,
        "title": "Structured Author Manuscript",
        "abstract": "This is a sufficiently long abstract content for validation.",
        "submission_email": "submissions@example.org",
        "authors": ["Alice Author", "Bob Author"],
        "author_contacts": [
            {
                "name": "Alice Author",
                "email": "alice.author@example.org",
                "affiliation": "Example University",
                "city": "Wuhan",
                "country_or_region": "China",
                "is_corresponding": True,
            },
            {
                "name": "Bob Author",
                "email": "bob.author@example.org",
                "affiliation": "Example Institute",
                "city": "Beijing",
                "country_or_region": "China",
                "is_corresponding": True,
            },
        ],
        "author_id": "00000000-0000-0000-0000-000000000000",
        "status": "pre_check",
        "created_at": "2026-01-28T00:00:00.000000+00:00",
        "updated_at": "2026-01-28T00:00:00.000000+00:00",
    }
    mock = get_full_mock([mock_data])
    admin_mock = get_full_mock([{"id": str(uuid.uuid4())}])
    mock_token = generate_test_token()

    with patch("app.lib.api_client.supabase", mock), \
         patch("app.api.v1.manuscripts.supabase", mock), \
         patch("app.api.v1.manuscripts.supabase_admin", admin_mock):
        response = await client.post(
            "/api/v1/manuscripts",
            json={
                "title": "Structured Author Manuscript",
                "abstract": "This is a sufficiently long abstract content for validation.",
                "submission_email": "submissions@example.org",
                "author_contacts": [
                    {
                        "name": "Alice Author",
                        "email": "alice.author@example.org",
                        "affiliation": "Example University",
                        "city": "Wuhan",
                        "country_or_region": "China",
                        "is_corresponding": True,
                    },
                    {
                        "name": "Bob Author",
                        "email": "bob.author@example.org",
                        "affiliation": "Example Institute",
                        "city": "Beijing",
                        "country_or_region": "China",
                        "is_corresponding": True,
                    },
                ],
                "author_id": "00000000-0000-0000-0000-000000000000",
                **required_submission_files("00000000-0000-0000-0000-000000000000"),
            },
            headers={"Authorization": f"Bearer {mock_token}"}
        )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_create_manuscript_rejects_duplicate_author_emails(client: AsyncClient):
    mock = get_full_mock([])
    mock_token = generate_test_token()

    with patch("app.lib.api_client.supabase", mock), \
         patch("app.api.v1.manuscripts.supabase", mock):
        response = await client.post(
            "/api/v1/manuscripts",
            json={
                "title": "Structured Author Manuscript",
                "abstract": "This is a sufficiently long abstract content for validation.",
                "submission_email": "submissions@example.org",
                "author_contacts": [
                    {
                        "name": "Alice Author",
                        "email": "alice.author@example.org",
                        "affiliation": "Example University",
                        "city": "Wuhan",
                        "country_or_region": "China",
                        "is_corresponding": True,
                    },
                    {
                        "name": "Alice Author",
                        "email": "ALICE.AUTHOR@example.org",
                        "affiliation": "Example Institute",
                        "city": "Beijing",
                        "country_or_region": "China",
                        "is_corresponding": False,
                    },
                ],
                "author_id": "00000000-0000-0000-0000-000000000000",
                **required_submission_files("00000000-0000-0000-0000-000000000000"),
            },
            headers={"Authorization": f"Bearer {mock_token}"}
        )

    assert response.status_code == 422
    assert "unique" in response.text.lower()


@pytest.mark.asyncio
async def test_create_manuscript_requires_city_and_country_for_each_author(client: AsyncClient):
    mock = get_full_mock([])
    mock_token = generate_test_token()

    with patch("app.lib.api_client.supabase", mock), \
         patch("app.api.v1.manuscripts.supabase", mock):
        response = await client.post(
            "/api/v1/manuscripts",
            json={
                "title": "Structured Author Manuscript",
                "abstract": "This is a sufficiently long abstract content for validation.",
                "submission_email": "submissions@example.org",
                "author_contacts": [
                    {
                        "name": "Alice Author",
                        "email": "alice.author@example.org",
                        "affiliation": "Example University",
                        "city": "",
                        "country_or_region": "China",
                        "is_corresponding": True,
                    }
                ],
                "author_id": "00000000-0000-0000-0000-000000000000",
                **required_submission_files("00000000-0000-0000-0000-000000000000"),
            },
            headers={"Authorization": f"Bearer {mock_token}"}
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_manuscript_rejects_invalid_journal_id(client: AsyncClient):
    """验证 journal_id 不存在时返回 422"""
    token_user_id = "11111111-1111-1111-1111-111111111111"
    mock = get_full_mock([])
    admin_mock = get_full_mock([])
    mock_token = generate_test_token(user_id=token_user_id)

    with patch("app.lib.api_client.supabase", mock), \
         patch("app.api.v1.manuscripts.supabase", mock), \
         patch("app.api.v1.manuscripts.supabase_admin", admin_mock):
        response = await client.post(
            "/api/v1/manuscripts",
            json={
                "title": "Invalid Journal Manuscript",
                "abstract": "This is a sufficiently long abstract content for validation.",
                "author_id": token_user_id,
                "journal_id": str(uuid.uuid4()),
                **required_submission_files(token_user_id),
            },
            headers={"Authorization": f"Bearer {mock_token}"}
        )

    assert response.status_code == 422
    assert "journal_id" in str(response.json().get("detail", "")).lower()


@pytest.mark.asyncio
async def test_create_manuscript_with_cover_letter_persists_metadata(client: AsyncClient):
    """验证作者提交 Word 主稿 + cover letter 时会写入 manuscript_files 元数据"""
    token_user_id = "11111111-1111-1111-1111-111111111111"
    manuscript_id = str(uuid.uuid4())
    mock_data = {
        "id": manuscript_id,
        "title": "Auth Bound Manuscript",
        "abstract": "This is a sufficiently long abstract content for validation.",
        "author_id": token_user_id,
        "status": "pre_check",
        "created_at": "2026-01-28T00:00:00.000000+00:00",
        "updated_at": "2026-01-28T00:00:00.000000+00:00"
    }
    mock = get_full_mock([mock_data])
    admin_mock = get_full_mock([{"id": str(uuid.uuid4())}])
    mock_token = generate_test_token(user_id=token_user_id)

    with patch("app.lib.api_client.supabase", mock), \
         patch("app.api.v1.manuscripts.supabase", mock), \
         patch("app.api.v1.manuscripts.supabase_admin", admin_mock):
        response = await client.post(
            "/api/v1/manuscripts",
            json={
                "title": "Auth Bound Manuscript",
                "abstract": "This is a sufficiently long abstract content for validation.",
                "submission_email": "corresponding@example.org",
                "author_contacts": required_author_contacts(),
                "author_id": token_user_id,
                **required_submission_files(token_user_id),
                "cover_letter_path": f"{token_user_id}/cover-letters/test_cover.docx",
                "cover_letter_filename": "test_cover.docx",
                "cover_letter_content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            },
            headers={"Authorization": f"Bearer {mock_token}"}
        )

    assert response.status_code == 200
    insert_payload = mock.insert.call_args[0][0]
    upsert_payloads = [call.args[0] for call in admin_mock.upsert.call_args_list]
    assert len(upsert_payloads) == 2
    word_payload = next(item for item in upsert_payloads if item["file_type"] == "manuscript")
    cover_payload = next(item for item in upsert_payloads if item["file_type"] == "cover_letter")
    assert word_payload["manuscript_id"] == insert_payload["id"]
    assert word_payload["path"].endswith("paper.docx")
    assert word_payload["uploaded_by"] == token_user_id
    assert cover_payload["manuscript_id"] == insert_payload["id"]
    assert cover_payload["bucket"] == "manuscripts"
    assert cover_payload["path"].endswith("test_cover.docx")
    assert cover_payload["uploaded_by"] == token_user_id


@pytest.mark.asyncio
async def test_create_manuscript_rejects_cover_letter_outside_user_scope(client: AsyncClient):
    """验证 cover_letter_path 必须属于当前用户目录"""
    token_user_id = "11111111-1111-1111-1111-111111111111"
    mock = get_full_mock([])
    mock_token = generate_test_token(user_id=token_user_id)

    with patch("app.lib.api_client.supabase", mock), \
         patch("app.api.v1.manuscripts.supabase", mock):
        response = await client.post(
            "/api/v1/manuscripts",
            json={
                "title": "Auth Bound Manuscript",
                "abstract": "This is a sufficiently long abstract content for validation.",
                "submission_email": "corresponding@example.org",
                "author_contacts": required_author_contacts(),
                "author_id": token_user_id,
                **required_submission_files(token_user_id),
                "cover_letter_path": "someone-else/cover-letters/test_cover.docx",
            },
            headers={"Authorization": f"Bearer {mock_token}"}
        )

    assert response.status_code == 422
    payload = response.json()
    assert "cover_letter_path" in str(payload.get("detail", ""))


@pytest.mark.asyncio
async def test_create_manuscript_rejects_missing_word_and_source_archive(client: AsyncClient):
    """验证 Word/ZIP 都缺失时返回 422"""
    token_user_id = "11111111-1111-1111-1111-111111111111"
    mock = get_full_mock([])
    mock_token = generate_test_token(user_id=token_user_id)

    with patch("app.lib.api_client.supabase", mock), \
         patch("app.api.v1.manuscripts.supabase", mock):
        response = await client.post(
            "/api/v1/manuscripts",
            json={
                "title": "Auth Bound Manuscript",
                "abstract": "This is a sufficiently long abstract content for validation.",
                "submission_email": "corresponding@example.org",
                "author_contacts": required_author_contacts(),
                "author_id": token_user_id,
                "file_path": f"{token_user_id}/paper.pdf",
                "cover_letter_path": f"{token_user_id}/cover-letters/cover-letter.pdf",
                "cover_letter_filename": "cover-letter.pdf",
                "cover_letter_content_type": "application/pdf",
            },
            headers={"Authorization": f"Bearer {mock_token}"}
        )

    assert response.status_code == 422
    assert "word manuscript or latex source zip" in str(response.json().get("detail", "")).lower()


@pytest.mark.asyncio
async def test_create_manuscript_rejects_missing_cover_letter(client: AsyncClient):
    """验证 cover letter 缺失时返回 422"""
    token_user_id = "11111111-1111-1111-1111-111111111111"
    mock = get_full_mock([])
    mock_token = generate_test_token(user_id=token_user_id)

    with patch("app.lib.api_client.supabase", mock), \
         patch("app.api.v1.manuscripts.supabase", mock):
        response = await client.post(
            "/api/v1/manuscripts",
            json={
                "title": "Auth Bound Manuscript",
                "abstract": "This is a sufficiently long abstract content for validation.",
                "submission_email": "corresponding@example.org",
                "author_contacts": required_author_contacts(),
                "author_id": token_user_id,
                "file_path": f"{token_user_id}/paper.pdf",
                "manuscript_word_path": f"{token_user_id}/word-manuscripts/paper.docx",
                "manuscript_word_filename": "paper.docx",
                "manuscript_word_content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            },
            headers={"Authorization": f"Bearer {mock_token}"}
        )

    assert response.status_code == 422
    assert "cover_letter_path" in str(response.json().get("detail", ""))


@pytest.mark.asyncio
async def test_create_manuscript_accepts_zip_source_archive(client: AsyncClient):
    """验证作者可用 ZIP 替代 Word 主稿提交"""
    token_user_id = "11111111-1111-1111-1111-111111111111"
    manuscript_id = str(uuid.uuid4())
    mock_data = {
        "id": manuscript_id,
        "title": "ZIP Source Manuscript",
        "abstract": "This is a sufficiently long abstract content for validation.",
        "submission_email": "corresponding@example.org",
        "authors": ["Alice Author", "Bob Author"],
        "author_contacts": required_author_contacts(),
        "author_id": token_user_id,
        "status": "pre_check",
        "created_at": "2026-01-28T00:00:00.000000+00:00",
        "updated_at": "2026-01-28T00:00:00.000000+00:00",
    }
    mock = get_full_mock([mock_data])
    admin_mock = get_full_mock([{"id": str(uuid.uuid4())}])
    mock_token = generate_test_token(user_id=token_user_id)

    with patch("app.lib.api_client.supabase", mock), \
         patch("app.api.v1.manuscripts.supabase", mock), \
         patch("app.api.v1.manuscripts.supabase_admin", admin_mock):
        response = await client.post(
            "/api/v1/manuscripts",
            json={
                "title": "ZIP Source Manuscript",
                "abstract": "This is a sufficiently long abstract content for validation.",
                "submission_email": "corresponding@example.org",
                "author_contacts": required_author_contacts(),
                "author_id": token_user_id,
                **required_zip_submission_files(token_user_id),
            },
            headers={"Authorization": f"Bearer {mock_token}"}
        )

    assert response.status_code == 200
    upsert_payloads = [call.args[0] for call in admin_mock.upsert.call_args_list]
    assert any(item["file_type"] == "source_archive" for item in upsert_payloads)
    source_archive_payload = next(item for item in upsert_payloads if item["file_type"] == "source_archive")
    assert source_archive_payload["path"].endswith("paper-source.zip")
    assert source_archive_payload["uploaded_by"] == token_user_id


@pytest.mark.asyncio
async def test_create_manuscript_rejects_word_and_source_archive_together(client: AsyncClient):
    """验证 Word 和 ZIP 不能同时提交"""
    token_user_id = "11111111-1111-1111-1111-111111111111"
    mock = get_full_mock([])
    mock_token = generate_test_token(user_id=token_user_id)

    with patch("app.lib.api_client.supabase", mock), \
         patch("app.api.v1.manuscripts.supabase", mock):
        response = await client.post(
            "/api/v1/manuscripts",
            json={
                "title": "Conflicting Source Files Manuscript",
                "abstract": "This is a sufficiently long abstract content for validation.",
                "submission_email": "corresponding@example.org",
                "author_contacts": required_author_contacts(),
                "author_id": token_user_id,
                **required_submission_files(token_user_id),
                "source_archive_path": f"{token_user_id}/source-archives/paper-source.zip",
                "source_archive_filename": "paper-source.zip",
                "source_archive_content_type": "application/zip",
            },
            headers={"Authorization": f"Bearer {mock_token}"}
        )

    assert response.status_code == 422
    assert "exactly one" in str(response.json().get("detail", "")).lower()

@pytest.mark.asyncio
async def test_get_manuscripts_list(client: AsyncClient, auth_token: str):
    """验证获取稿件列表接口"""
    mock_data = [
        {"id": str(uuid.uuid4()), "title": "Paper 1", "status": "pre_check"},
        {"id": str(uuid.uuid4()), "title": "Paper 2", "status": "under_review"}
    ]
    mock = get_full_mock(mock_data)
    with patch("app.lib.api_client.supabase", mock), \
         patch("app.api.v1.manuscripts.supabase", mock):
        response = await client.get("/api/v1/manuscripts", headers={"Authorization": f"Bearer {auth_token}"})
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
        get_response = await client.get("/api/v1/manuscripts", headers={"Authorization": f"Bearer {mock_token}"})
        assert get_response.status_code == 200

    # 测试 POST 路由（使用相同的路径）
    mock_data = [{
        "id": str(uuid.uuid4()),
        "title": "Test",
        "submission_email": "corresponding@example.org",
        "authors": ["Alice Author"],
        "author_contacts": [required_author_contacts()[0]],
    }]
    mock = get_full_mock(mock_data)
    admin_mock = get_full_mock([{"id": str(uuid.uuid4())}])
    with patch("app.lib.api_client.supabase", mock), \
         patch("app.api.v1.manuscripts.supabase", mock), \
         patch("app.api.v1.manuscripts.supabase_admin", admin_mock):
        post_response = await client.post(
            "/api/v1/manuscripts",
            json={
                "title": "Valid Title",
                "abstract": "This is a sufficiently long abstract content for validation.",
                "submission_email": "corresponding@example.org",
                "author_contacts": [required_author_contacts()[0]],
                "author_id": "00000000-0000-0000-0000-000000000000",
                **required_submission_files("00000000-0000-0000-0000-000000000000"),
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
async def test_upload_success_returns_trace_id(client: AsyncClient):
    """验证上传成功时返回 trace_id，便于线上日志排查"""

    async def fake_parse(_text: str, *, parser_mode: str, layout_lines=None):
        assert parser_mode == "pdf"
        return {
            "title": "AI Paper",
            "abstract": "A study",
            "authors": ["Alice"],
            "parser_source": "gemini",
        }

    with patch(
        "app.api.v1.manuscripts.extract_text_and_layout_from_pdf",
        return_value=("mocked text", []),
    ), patch("app.api.v1.manuscripts.extract_manuscript_metadata", fake_parse):
        files = {"file": ("paper.pdf", b"%PDF-1.4\n%mocked", "application/pdf")}
        response = await client.post("/api/v1/manuscripts/upload", files=files)

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["title"] == "AI Paper"
    assert payload["data"]["parser_source"] == "gemini"
    assert isinstance(payload.get("trace_id"), str)
    assert re.fullmatch(r"[0-9a-f]{8}", payload["trace_id"]) is not None


@pytest.mark.asyncio
async def test_upload_docx_success_returns_trace_id(client: AsyncClient):
    """验证 DOCX 上传也可返回自动解析结果（用于预填标题/摘要）"""

    async def fake_parse(_text: str, *, parser_mode: str, layout_lines=None):
        assert parser_mode == "docx"
        return {
            "title": "DOCX Paper",
            "abstract": "DOCX abstract",
            "authors": ["Bob"],
            "author_contacts": [
                {
                    "name": "Bob Li",
                    "email": "bob.li@example.edu",
                    "affiliation": "Wuhan University",
                    "city": "Wuhan",
                    "country_or_region": "China",
                    "is_corresponding": True,
                }
            ],
            "parser_source": "gemini+local_fill",
        }

    with patch(
        "app.api.v1.manuscripts.extract_text_from_docx",
        return_value="mocked docx text",
    ), patch("app.api.v1.manuscripts.extract_manuscript_metadata", fake_parse):
        files = {
            "file": (
                "paper.docx",
                b"PK\x03\x04mocked-docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        }
        response = await client.post("/api/v1/manuscripts/upload", files=files)

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["title"] == "DOCX Paper"
    assert payload["data"]["author_contacts"][0]["email"] == "bob.li@example.edu"
    assert payload["data"]["parser_source"] == "gemini+local_fill"
    assert isinstance(payload.get("trace_id"), str)
    assert re.fullmatch(r"[0-9a-f]{8}", payload["trace_id"]) is not None


@pytest.mark.asyncio
async def test_upload_metadata_timeout_returns_manual_fill_hint(client: AsyncClient, monkeypatch):
    monkeypatch.setenv("MANUSCRIPT_METADATA_TIMEOUT_SEC", "0.01")

    async def slow_extract(*args, **kwargs):
        await asyncio.sleep(0.1)
        return {"title": "Late"}

    with patch(
        "app.api.v1.manuscripts.extract_text_from_docx",
        return_value="mocked docx text",
    ), patch("app.api.v1.manuscripts.extract_manuscript_metadata", side_effect=slow_extract):
        files = {
            "file": (
                "paper.docx",
                b"PK\x03\x04mocked-docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        }
        response = await client.post("/api/v1/manuscripts/upload", files=files)

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["parser_source"] == "timeout"
    assert payload["data"]["author_contacts"] == []
    assert "手动填写" in payload["message"]


@pytest.mark.asyncio
async def test_upload_doc_legacy_returns_manual_fill_hint(client: AsyncClient):
    """验证 .doc（旧格式）走手动填写降级提示，而不是 500"""
    files = {"file": ("paper.doc", b"legacy-binary", "application/msword")}
    response = await client.post("/api/v1/manuscripts/upload", files=files)

    assert response.status_code == 200
    payload = response.json()
    assert payload.get("success") is True
    assert payload.get("data") == {"title": "", "abstract": "", "authors": [], "author_contacts": []}
    assert ".doc" in str(payload.get("message", ""))


@pytest.mark.asyncio
async def test_quality_check_endpoint_calls_service(client: AsyncClient):
    """验证质检接口调用 service 并返回结果"""
    from uuid import uuid4

    manuscript_id = uuid4()
    expected = {"manuscript_id": str(manuscript_id), "passed": True}

    async def fake_quality_check(_manuscript_id, passed, _owner_id):
        return {"manuscript_id": str(_manuscript_id), "passed": passed}

    with patch("app.api.v1.manuscripts.process_quality_check", fake_quality_check), patch(
        "app.api.v1.manuscripts.validate_internal_owner_id", lambda _id: {}
    ):
        response = await client.post(
            f"/api/v1/manuscripts/{manuscript_id}/quality-check",
            json={
                "passed": True,
                "owner_id": "00000000-0000-0000-0000-000000000000",
            },
        )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["data"] == expected
