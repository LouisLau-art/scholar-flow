import pytest
from httpx import AsyncClient
from unittest.mock import MagicMock, patch
from uuid import uuid4
from postgrest.exceptions import APIError

from .test_utils import insert_manuscript, make_user


def _mock_storage_upload():
    """
    Mock Supabase Storage 上传，避免集成测试依赖真实 Storage 服务。
    """
    storage = MagicMock()
    bucket = MagicMock()
    bucket.upload.return_value = {"success": True}
    storage.from_.return_value = bucket
    return storage


def _cleanup_revision_artifacts(db, manuscript_id: str) -> None:
    # 中文注释: Supabase-py 无事务；测试结束必须手动清理，避免污染后续测试与本地数据。
    for table, column in (
        ("review_assignments", "manuscript_id"),
        ("revisions", "manuscript_id"),
        ("manuscript_versions", "manuscript_id"),
        ("notifications", "manuscript_id"),
    ):
        try:
            db.table(table).delete().eq(column, manuscript_id).execute()
        except Exception:
            pass
    try:
        db.table("manuscripts").delete().eq("id", manuscript_id).execute()
    except Exception:
        pass


def _require_revision_schema(db) -> None:
    """
    若目标数据库未具备修订工作流所需表/列，则跳过测试。

    中文注释:
    - 本仓库支持“本地 Supabase（推荐）”与“远端 Supabase（可能滞后）”两种环境。
    - 当远端 schema 未同步（例如缺少 manuscripts.version）时，本测试应跳过而不是误报失败。
    """
    checks = [
        ("manuscripts", "id,author_id,status,file_path,version"),
        ("revisions", "id,manuscript_id,round_number,decision_type,editor_comment,status"),
        ("manuscript_versions", "id,manuscript_id,version_number,file_path"),
        ("review_assignments", "id,manuscript_id,reviewer_id,round_number,status"),
    ]
    for table, select_cols in checks:
        try:
            db.table(table).select(select_cols).limit(1).execute()
        except APIError as e:
            pytest.skip(f"数据库缺少修订测试所需 schema（{table} / {select_cols}）：{getattr(e, 'message', str(e))}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_happy_path_revision_loop(
    client: AsyncClient,
    supabase_admin_client,
    set_admin_emails,
):
    """
    场景 1：标准修订循环

    1) Editor 请求修订 -> manuscripts.status=revision_requested + revisions(pending) + v1 快照
    2) Author 提交修订 -> manuscripts.status=resubmitted + version=2 + revisions(submitted) + v2 记录
    3) Editor 指派审稿人 -> review_assignments.round_number=2
    """

    # Editor 通过 ADMIN_EMAILS 触发 editor/admin 权限（避免依赖 user_profiles/RLS）
    editor = make_user(email="editor_e2e@example.com")
    set_admin_emails([editor.email])

    author = make_user(email="author_e2e@example.com")

    manuscript_id = str(uuid4())
    v1_path = f"{manuscript_id}/v1_initial.pdf"
    _require_revision_schema(supabase_admin_client)
    insert_manuscript(
        supabase_admin_client,
        manuscript_id=manuscript_id,
        author_id=author.id,
        status="pending_decision",
        version=1,
        file_path=v1_path,
        title="Revision Cycle Manuscript",
    )

    try:
        # --- Step 1: Editor requests revision ---
        res = await client.post(
            "/api/v1/editor/revisions",
            headers={"Authorization": f"Bearer {editor.token}"},
            json={
                "manuscript_id": manuscript_id,
                "decision_type": "major",
                "comment": "Please address reviewer concerns and fix typos.",
            },
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["success"] is True
        assert body["data"]["status"] == "pending"
        assert body["data"]["round_number"] == 1

        ms = (
            supabase_admin_client.table("manuscripts")
            .select("status, version, file_path")
            .eq("id", manuscript_id)
            .single()
            .execute()
            .data
        )
        assert ms["status"] == "revision_requested"
        assert ms.get("version", 1) == 1
        assert ms.get("file_path") == v1_path

        revs = (
            supabase_admin_client.table("revisions")
            .select("round_number, status, decision_type")
            .eq("manuscript_id", manuscript_id)
            .order("round_number", desc=True)
            .limit(1)
            .execute()
            .data
            or []
        )
        assert revs and revs[0]["round_number"] == 1
        assert revs[0]["status"] == "pending"
        assert revs[0]["decision_type"] == "major"

        v1 = (
            supabase_admin_client.table("manuscript_versions")
            .select("version_number, file_path")
            .eq("manuscript_id", manuscript_id)
            .eq("version_number", 1)
            .limit(1)
            .execute()
            .data
            or []
        )
        assert v1 and v1[0]["file_path"] == v1_path

        # --- Step 2: Author submits revision (mock storage upload) ---
        mocked_storage = _mock_storage_upload()
        mocked_admin_client = MagicMock()
        mocked_admin_client.storage = mocked_storage
        with patch("app.api.v1.manuscripts.supabase_admin", new=mocked_admin_client):
            res2 = await client.post(
                f"/api/v1/manuscripts/{manuscript_id}/revisions",
                headers={"Authorization": f"Bearer {author.token}"},
                data={"response_letter": "I have addressed all comments point-by-point in this revision."},
                files={
                    "file": (
                        "revised.pdf",
                        b"%PDF-1.4\n% mocked pdf\n",
                        "application/pdf",
                    )
                },
            )
        assert res2.status_code == 200, res2.text
        body2 = res2.json()
        assert body2["success"] is True

        ms2 = (
            supabase_admin_client.table("manuscripts")
            .select("status, version, file_path")
            .eq("id", manuscript_id)
            .single()
            .execute()
            .data
        )
        assert ms2["status"] == "resubmitted"
        assert ms2["version"] == 2
        assert ms2["file_path"].startswith(f"{manuscript_id}/v2_")

        revs2 = (
            supabase_admin_client.table("revisions")
            .select("round_number, status, submitted_at")
            .eq("manuscript_id", manuscript_id)
            .order("round_number", desc=True)
            .limit(1)
            .execute()
            .data
            or []
        )
        assert revs2 and revs2[0]["round_number"] == 1
        assert revs2[0]["status"] == "submitted"
        assert revs2[0].get("submitted_at")

        v2 = (
            supabase_admin_client.table("manuscript_versions")
            .select("version_number, file_path")
            .eq("manuscript_id", manuscript_id)
            .eq("version_number", 2)
            .limit(1)
            .execute()
            .data
            or []
        )
        assert v2 and v2[0]["file_path"] == ms2["file_path"]

        # --- Step 3: Editor assigns reviewers ---
        reviewer_id = str(uuid4())
        res3 = await client.post(
            "/api/v1/reviews/assign",
            headers={"Authorization": f"Bearer {editor.token}"},
            json={"manuscript_id": manuscript_id, "reviewer_id": reviewer_id},
        )
        assert res3.status_code == 200, res3.text
        body3 = res3.json()
        assert body3.get("success") is True
        assert "data" in body3, "assign endpoint fell back to mock-success path"
        assert body3["data"]["round_number"] == 2

        ra = (
            supabase_admin_client.table("review_assignments")
            .select("round_number, reviewer_id, manuscript_id")
            .eq("manuscript_id", manuscript_id)
            .eq("reviewer_id", reviewer_id)
            .limit(1)
            .execute()
            .data
            or []
        )
        assert ra and ra[0]["round_number"] == 2
    finally:
        _cleanup_revision_artifacts(supabase_admin_client, manuscript_id)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_editor_can_request_revision_from_resubmitted(
    client: AsyncClient,
    supabase_admin_client,
    set_admin_emails,
):
    """
    场景：作者修回 (resubmitted) 后，Editor 仍可“再退回一轮修订”（大修/小修）。

    目标：
    - /api/v1/editor/revisions 在 resubmitted 状态可用
    - round_number 正确递增（已有 round 1 -> 新建 round 2）
    - manuscripts.status 推进到 revision_requested
    """

    editor = make_user(email="editor_resubmitted@example.com")
    set_admin_emails([editor.email])

    author = make_user(email="author_resubmitted@example.com")

    manuscript_id = str(uuid4())
    v2_path = f"{manuscript_id}/v2_resubmitted.pdf"
    _require_revision_schema(supabase_admin_client)
    insert_manuscript(
        supabase_admin_client,
        manuscript_id=manuscript_id,
        author_id=author.id,
        status="resubmitted",
        version=2,
        file_path=v2_path,
        title="Resubmitted Manuscript",
    )

    try:
        # 先模拟历史上已经有一轮修订（round 1 已提交）
        supabase_admin_client.table("revisions").insert(
            {
                "manuscript_id": manuscript_id,
                "round_number": 1,
                "decision_type": "major",
                "editor_comment": "Round 1 comment",
                "status": "submitted",
                "response_letter": "Round 1 response",
            }
        ).execute()

        # Editor 再退回小修（round 2）
        res = await client.post(
            "/api/v1/editor/revisions",
            headers={"Authorization": f"Bearer {editor.token}"},
            json={
                "manuscript_id": manuscript_id,
                "decision_type": "minor",
                "comment": "Please make minor fixes.",
            },
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["success"] is True
        assert body["data"]["round_number"] == 2
        assert body["data"]["status"] == "pending"

        ms = (
            supabase_admin_client.table("manuscripts")
            .select("status")
            .eq("id", manuscript_id)
            .single()
            .execute()
            .data
        )
        assert ms["status"] == "revision_requested"
    finally:
        _cleanup_revision_artifacts(supabase_admin_client, manuscript_id)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_rbac_enforcement(
    client: AsyncClient,
    supabase_admin_client,
    set_admin_emails,
):
    """
    场景 2：RBAC 约束

    - 非 editor/admin 不能请求修订
    - author 不能请求修订
    - editor 不能代替 author 提交修订
    """

    editor = make_user(email="editor_rbac@example.com")
    set_admin_emails([editor.email])

    author = make_user(email="author_rbac@example.com")
    random_user = make_user(email="random_rbac@example.com")

    manuscript_id = str(uuid4())
    _require_revision_schema(supabase_admin_client)
    insert_manuscript(
        supabase_admin_client,
        manuscript_id=manuscript_id,
        author_id=author.id,
        status="pending_decision",
        version=1,
        file_path=f"{manuscript_id}/v1_initial.pdf",
        title="RBAC Manuscript",
    )

    try:
        # Random user tries to request revision -> 403
        res1 = await client.post(
            "/api/v1/editor/revisions",
            headers={"Authorization": f"Bearer {random_user.token}"},
            json={
                "manuscript_id": manuscript_id,
                "decision_type": "minor",
                "comment": "This should not be allowed.",
            },
        )
        assert res1.status_code == 403

        # Author tries to request revision -> 403
        res2 = await client.post(
            "/api/v1/editor/revisions",
            headers={"Authorization": f"Bearer {author.token}"},
            json={
                "manuscript_id": manuscript_id,
                "decision_type": "minor",
                "comment": "Authors cannot request revision on their own.",
            },
        )
        assert res2.status_code == 403

        # Editor tries to submit revision for author -> 403 (blocked before storage upload)
        res3 = await client.post(
            f"/api/v1/manuscripts/{manuscript_id}/revisions",
            headers={"Authorization": f"Bearer {editor.token}"},
            data={"response_letter": "This should be rejected: editor is not author."},
            files={
                "file": (
                    "revised.pdf",
                    b"%PDF-1.4\n% mocked pdf\n",
                    "application/pdf",
                )
            },
        )
        assert res3.status_code == 403
    finally:
        _cleanup_revision_artifacts(supabase_admin_client, manuscript_id)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_file_safety(
    client: AsyncClient,
    supabase_admin_client,
    set_admin_emails,
):
    """
    场景 3：文件安全（v1 不被覆盖）

    - v1 的 file_path 必须保留在 manuscript_versions(version_number=1)
    - manuscript.file_path 必须更新为 v2 的版本化路径
    """

    editor = make_user(email="editor_filesafety@example.com")
    set_admin_emails([editor.email])
    author = make_user(email="author_filesafety@example.com")

    manuscript_id = str(uuid4())
    v1_path = f"{manuscript_id}/v1_test.pdf"
    _require_revision_schema(supabase_admin_client)
    insert_manuscript(
        supabase_admin_client,
        manuscript_id=manuscript_id,
        author_id=author.id,
        status="pending_decision",
        version=1,
        file_path=v1_path,
        title="File Safety Manuscript",
    )

    try:
        res = await client.post(
            "/api/v1/editor/revisions",
            headers={"Authorization": f"Bearer {editor.token}"},
            json={
                "manuscript_id": manuscript_id,
                "decision_type": "minor",
                "comment": "Please fix formatting issues and update citations.",
            },
        )
        assert res.status_code == 200, res.text

        mocked_storage = _mock_storage_upload()
        mocked_admin_client = MagicMock()
        mocked_admin_client.storage = mocked_storage
        with patch("app.api.v1.manuscripts.supabase_admin", new=mocked_admin_client):
            res2 = await client.post(
                f"/api/v1/manuscripts/{manuscript_id}/revisions",
                headers={"Authorization": f"Bearer {author.token}"},
                data={
                    "response_letter": "I have fixed all formatting issues and updated citations accordingly."
                },
                files={
                    "file": (
                        "v2_test.pdf",
                        b"%PDF-1.4\n% mocked pdf\n",
                        "application/pdf",
                    )
                },
            )
        assert res2.status_code == 200, res2.text

        ms = (
            supabase_admin_client.table("manuscripts")
            .select("file_path, version, status")
            .eq("id", manuscript_id)
            .single()
            .execute()
            .data
        )
        assert ms["status"] == "resubmitted"
        assert ms["version"] == 2
        assert ms["file_path"].startswith(f"{manuscript_id}/v2_")

        v1 = (
            supabase_admin_client.table("manuscript_versions")
            .select("version_number, file_path")
            .eq("manuscript_id", manuscript_id)
            .eq("version_number", 1)
            .limit(1)
            .execute()
            .data
            or []
        )
        assert v1 and v1[0]["file_path"] == v1_path
    finally:
        _cleanup_revision_artifacts(supabase_admin_client, manuscript_id)
