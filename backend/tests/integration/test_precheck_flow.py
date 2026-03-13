import pytest
from types import SimpleNamespace
from uuid import uuid4

from app.core.auth_utils import get_current_user
from app.core.roles import get_current_profile
from app.models.manuscript import ManuscriptStatus, PreCheckStatus
from main import app

# Mock data for integration tests
MOCK_ME_ID = str(uuid4())
MOCK_AE_ID = str(uuid4())
MOCK_EIC_ID = str(uuid4())
MOCK_MANUSCRIPT_ID = str(uuid4())

@pytest.fixture
def mock_db_session(mocker):
    """Mock database session for integration tests"""
    mock_session = mocker.MagicMock()
    return mock_session

@pytest.fixture(autouse=True)
def bypass_auth(mocker):
    """Bypass auth and profile for all tests in this file"""
    app.dependency_overrides[get_current_user] = lambda: {"id": MOCK_ME_ID, "email": "test@example.com"}
    app.dependency_overrides[get_current_profile] = lambda: {"id": MOCK_ME_ID, "roles": ["admin", "managing_editor", "assistant_editor", "editor_in_chief"]}
    yield
    app.dependency_overrides = {}

async def test_me_intake_flow(client, mocker):
    """
    T004: Integration test for ME intake flow.
    1. List manuscripts in intake queue.
    2. Assign AE to a manuscript.
    """
    # Mock authentication as ME
    mocker.patch("app.core.auth_utils.get_current_user", return_value={"id": MOCK_ME_ID, "roles": ["managing_editor"]})
    
    # Mock DB response for list
    mock_manuscript = {
        "id": MOCK_MANUSCRIPT_ID,
        "title": "Test Manuscript",
        "status": ManuscriptStatus.PRE_CHECK.value,
        "pre_check_status": PreCheckStatus.INTAKE.value,
        "abstract": "Abstract content...",
        "created_at": "2026-02-06T00:00:00Z",
        "updated_at": "2026-02-06T00:00:00Z"
    }
    
    # Mock service layer instead of raw DB for integration test focus on API/Controller logic
    mocker.patch("app.services.editor_service.EditorService.get_intake_queue", return_value=[mock_manuscript])
    mocker.patch(
        "app.services.editor_service.EditorService.assign_ae",
        return_value={
            "id": MOCK_MANUSCRIPT_ID,
            "status": ManuscriptStatus.PRE_CHECK.value,
            "pre_check_status": PreCheckStatus.TECHNICAL.value,
            "assistant_editor_id": MOCK_AE_ID,
        },
    )

    # 1. Test List Intake Queue
    response = await client.get("/api/v1/editor/intake")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == MOCK_MANUSCRIPT_ID
    assert data[0]["pre_check_status"] == "intake"

    # 2. Test Assign AE
    response = await client.post(f"/api/v1/editor/manuscripts/{MOCK_MANUSCRIPT_ID}/assign-ae", json={"ae_id": MOCK_AE_ID})
    assert response.status_code == 200
    assert response.json()["message"] == "AE assigned successfully"


async def test_me_assign_ae_waiting_author_flow(client, mocker):
    mocker.patch(
        "app.services.editor_service.EditorService.assign_ae",
        return_value={
            "id": MOCK_MANUSCRIPT_ID,
            "status": ManuscriptStatus.REVISION_BEFORE_REVIEW.value,
            "pre_check_status": PreCheckStatus.TECHNICAL.value,
            "assistant_editor_id": MOCK_AE_ID,
        },
    )

    response = await client.post(
        f"/api/v1/editor/manuscripts/{MOCK_MANUSCRIPT_ID}/assign-ae",
        json={"ae_id": MOCK_AE_ID},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "AE assigned successfully"
    assert body["data"]["status"] == ManuscriptStatus.REVISION_BEFORE_REVIEW.value
    assert body["data"]["pre_check_status"] == PreCheckStatus.TECHNICAL.value


async def test_ae_check_flow(client, mocker):
    """
    T011: Integration test for AE check flow.
    1. List manuscripts in AE workspace.
    2. Submit technical check.
    """
    # Mock authentication as AE
    mocker.patch("app.core.auth_utils.get_current_user", return_value={"id": MOCK_AE_ID, "roles": ["assistant_editor"]})
    
    # Mock DB response for list
    mock_manuscript = {
        "id": MOCK_MANUSCRIPT_ID,
        "title": "Test Manuscript",
        "status": ManuscriptStatus.PRE_CHECK.value,
        "pre_check_status": PreCheckStatus.TECHNICAL.value,
        "assistant_editor_id": MOCK_AE_ID,
        "abstract": "Abstract content...",
        "created_at": "2026-02-06T00:00:00Z",
        "updated_at": "2026-02-06T00:00:00Z"
    }

    mocker.patch("app.services.editor_service.EditorService.get_ae_workspace", return_value=[mock_manuscript])
    mocker.patch(
        "app.services.editor_service.EditorService.submit_technical_check",
        return_value={
            "id": MOCK_MANUSCRIPT_ID,
            "status": ManuscriptStatus.PRE_CHECK.value,
            "pre_check_status": PreCheckStatus.ACADEMIC.value,
        },
    )

    # 1. Test List AE Workspace
    response = await client.get("/api/v1/editor/workspace")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["assistant_editor_id"] == MOCK_AE_ID

    # 2. Test Submit Check
    response = await client.post(
        f"/api/v1/editor/manuscripts/{MOCK_MANUSCRIPT_ID}/submit-check",
        json={"decision": "pass", "comment": "looks good"},
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Technical check submitted"


async def test_submit_technical_check_passes_academic_editor_id_to_service(client, mocker):
    mocker.patch("app.core.auth_utils.get_current_user", return_value={"id": MOCK_AE_ID, "roles": ["assistant_editor"]})
    submit_mock = mocker.patch(
        "app.services.editor_service.EditorService.submit_technical_check",
        return_value={
            "id": MOCK_MANUSCRIPT_ID,
            "status": ManuscriptStatus.PRE_CHECK.value,
            "pre_check_status": PreCheckStatus.ACADEMIC.value,
        },
    )

    academic_editor_id = str(uuid4())
    response = await client.post(
        f"/api/v1/editor/manuscripts/{MOCK_MANUSCRIPT_ID}/submit-check",
        json={
            "decision": "academic",
            "comment": "send to academic committee",
            "academic_editor_id": academic_editor_id,
        },
    )

    assert response.status_code == 200
    assert submit_mock.call_args.kwargs["academic_editor_id"] == academic_editor_id


async def test_list_academic_editors_filters_by_manuscript_and_search(client, mocker):
    list_mock = mocker.patch(
        "app.services.editor_service.EditorService.list_academic_editor_candidates",
        return_value=[
            {
                "id": str(uuid4()),
                "email": "academic@example.com",
                "full_name": "Academic Editor",
                "roles": ["academic_editor"],
            }
        ],
    )

    response = await client.get(
        f"/api/v1/editor/academic-editors?manuscript_id={MOCK_MANUSCRIPT_ID}&search=academic"
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert str(list_mock.call_args.kwargs["manuscript_id"]) == MOCK_MANUSCRIPT_ID
    assert list_mock.call_args.kwargs["search"] == "academic"


async def test_bind_academic_editor_passes_reason_and_source(client, mocker):
    bind_mock = mocker.patch(
        "app.services.editor_service.EditorService.bind_academic_editor",
        return_value={
            "id": MOCK_MANUSCRIPT_ID,
            "academic_editor_id": MOCK_EIC_ID,
        },
    )

    response = await client.post(
        f"/api/v1/editor/manuscripts/{MOCK_MANUSCRIPT_ID}/bind-academic-editor",
        json={
            "academic_editor_id": MOCK_EIC_ID,
            "reason": "Switch to journal chair for final academic review",
            "source": "manuscript_detail",
        },
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert bind_mock.call_args.kwargs["reason"] == "Switch to journal chair for final academic review"
    assert bind_mock.call_args.kwargs["source"] == "manuscript_detail"


async def test_revert_technical_check_flow(client, mocker):
    """
    AE/ME 受控回退接口集成校验。
    """
    mocker.patch("app.core.auth_utils.get_current_user", return_value={"id": MOCK_AE_ID, "roles": ["assistant_editor"]})
    mocker.patch(
        "app.services.editor_service.EditorService.revert_technical_check",
        return_value={
            "id": MOCK_MANUSCRIPT_ID,
            "status": ManuscriptStatus.PRE_CHECK.value,
            "pre_check_status": PreCheckStatus.TECHNICAL.value,
            "assistant_editor_id": MOCK_AE_ID,
        },
    )

    response = await client.post(
        f"/api/v1/editor/manuscripts/{MOCK_MANUSCRIPT_ID}/revert-technical-check",
        json={"reason": "误触提交外审，需要撤回到技术检查阶段"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Technical check reverted"
    assert body["data"]["status"] == ManuscriptStatus.PRE_CHECK.value
    assert body["data"]["pre_check_status"] == PreCheckStatus.TECHNICAL.value


async def test_author_submit_revision_uses_persisted_precheck_stage_when_pending_has_no_hint(client, mocker):
    author_id = str(uuid4())
    assistant_editor_id = str(uuid4())
    app.dependency_overrides[get_current_user] = lambda: {"id": author_id, "email": "author@example.com"}

    revision_service = mocker.Mock()
    revision_service.get_manuscript.return_value = {
        "id": MOCK_MANUSCRIPT_ID,
        "title": "Waiting Author Manuscript",
        "status": ManuscriptStatus.REVISION_BEFORE_REVIEW.value,
        "pre_check_status": PreCheckStatus.TECHNICAL.value,
        "assistant_editor_id": assistant_editor_id,
        "author_id": author_id,
        "version": 1,
    }
    revision_service.ensure_pending_revision_for_submit.return_value = {
        "id": "rev-1",
        "decision_type": "minor",
    }
    revision_service.generate_versioned_file_path.side_effect = [
        f"{MOCK_MANUSCRIPT_ID}/v2_revision.pdf",
        f"{MOCK_MANUSCRIPT_ID}/v2_revision.docx",
    ]
    revision_service.resolve_precheck_resubmit_stage.return_value = PreCheckStatus.TECHNICAL.value
    revision_service.submit_revision.return_value = {
        "success": True,
        "data": {
            "manuscript_status": ManuscriptStatus.PRE_CHECK.value,
            "pre_check_status": PreCheckStatus.TECHNICAL.value,
        },
    }
    mocker.patch("app.api.v1.manuscripts_submission.RevisionService", return_value=revision_service)

    storage_bucket = mocker.Mock()
    storage_bucket.upload.return_value = None
    supabase_admin = mocker.Mock()
    supabase_admin.storage.from_.return_value = storage_bucket
    supabase_admin.table.return_value.upsert.return_value.execute.return_value = SimpleNamespace(data=[{"id": "file-1"}])
    mocker.patch(
        "app.api.v1.manuscripts_submission._m",
        return_value=SimpleNamespace(
            supabase_admin=supabase_admin,
            _is_missing_table_error=lambda *_args, **_kwargs: False,
        ),
    )

    notification_service = mocker.Mock()
    mocker.patch("app.api.v1.manuscripts_submission.NotificationService", return_value=notification_service)

    response = await client.post(
        f"/api/v1/manuscripts/{MOCK_MANUSCRIPT_ID}/revisions",
        data={"response_letter": "已按意见完成技术修改。"},
        files={
            "pdf_file": ("revised.pdf", b"%PDF-1.4 mocked", "application/pdf"),
            "word_file": (
                "revised.docx",
                b"PK\x03\x04 mocked docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
        },
    )

    assert response.status_code == 200
    assert revision_service.submit_revision.call_args.kwargs["precheck_resubmit_stage"] == PreCheckStatus.TECHNICAL.value
    notification_service.create_notification.assert_called()


async def test_author_submit_revision_falls_back_to_intake_when_resubmit_stage_has_no_assigned_ae(client, mocker):
    author_id = str(uuid4())
    app.dependency_overrides[get_current_user] = lambda: {"id": author_id, "email": "author@example.com"}

    revision_service = mocker.Mock()
    revision_service.get_manuscript.return_value = {
        "id": MOCK_MANUSCRIPT_ID,
        "title": "Waiting Author Intake Fallback",
        "status": ManuscriptStatus.REVISION_BEFORE_REVIEW.value,
        "pre_check_status": PreCheckStatus.TECHNICAL.value,
        "assistant_editor_id": None,
        "author_id": author_id,
        "version": 2,
    }
    revision_service.ensure_pending_revision_for_submit.return_value = {
        "id": "rev-2",
        "decision_type": "minor",
        "__derived_precheck_stage": PreCheckStatus.TECHNICAL.value,
    }
    revision_service.resolve_precheck_resubmit_stage.return_value = PreCheckStatus.INTAKE.value
    revision_service.generate_versioned_file_path.side_effect = [
        f"{MOCK_MANUSCRIPT_ID}/v3_revision.pdf",
        f"{MOCK_MANUSCRIPT_ID}/v3_revision.docx",
    ]
    revision_service.submit_revision.return_value = {
        "success": True,
        "data": {
            "manuscript_status": ManuscriptStatus.PRE_CHECK.value,
            "pre_check_status": PreCheckStatus.INTAKE.value,
        },
    }
    mocker.patch("app.api.v1.manuscripts_submission.RevisionService", return_value=revision_service)

    storage_bucket = mocker.Mock()
    storage_bucket.upload.return_value = None
    supabase_admin = mocker.Mock()
    supabase_admin.storage.from_.return_value = storage_bucket
    supabase_admin.table.return_value.upsert.return_value.execute.return_value = SimpleNamespace(data=[{"id": "file-2"}])
    mocker.patch(
        "app.api.v1.manuscripts_submission._m",
        return_value=SimpleNamespace(
            supabase_admin=supabase_admin,
            _is_missing_table_error=lambda *_args, **_kwargs: False,
        ),
    )

    notification_service = mocker.Mock()
    mocker.patch("app.api.v1.manuscripts_submission.NotificationService", return_value=notification_service)

    response = await client.post(
        f"/api/v1/manuscripts/{MOCK_MANUSCRIPT_ID}/revisions",
        data={"response_letter": "作者已完成修订并重新提交。"},
        files={
            "pdf_file": ("revised.pdf", b"%PDF-1.4 mocked", "application/pdf"),
            "word_file": (
                "revised.docx",
                b"PK\x03\x04 mocked docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
        },
    )

    assert response.status_code == 200
    assert revision_service.submit_revision.call_args.kwargs["precheck_resubmit_stage"] == PreCheckStatus.INTAKE.value
    notification_service.create_notification.assert_called()


async def test_me_workspace_flow(client, mocker):
    """
    Managing Editor Workspace 接口集成校验。
    """
    mocker.patch("app.core.auth_utils.get_current_user", return_value={"id": MOCK_ME_ID, "roles": ["managing_editor"]})
    mock_rows = [
        {
            "id": MOCK_MANUSCRIPT_ID,
            "title": "ME Workspace Manuscript",
            "status": ManuscriptStatus.PRE_CHECK.value,
            "pre_check_status": PreCheckStatus.INTAKE.value,
            "workspace_bucket": "intake",
            "owner_id": MOCK_ME_ID,
        }
    ]
    mocker.patch("app.services.editor_service.EditorService.get_managing_workspace", return_value=mock_rows)

    response = await client.get("/api/v1/editor/managing-workspace")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["workspace_bucket"] == "intake"


async def test_eic_check_flow(client, mocker):
    """
    T017: Integration test for EIC academic check flow.
    1. List manuscripts in academic queue.
    2. Submit academic check (Pass -> Review).
    """
    # Mock authentication as EIC
    mocker.patch("app.core.auth_utils.get_current_user", return_value={"id": MOCK_EIC_ID, "roles": ["editor_in_chief"]})
    
    # Mock DB response
    mock_manuscript = {
        "id": MOCK_MANUSCRIPT_ID,
        "title": "Test Manuscript",
        "status": ManuscriptStatus.PRE_CHECK.value,
        "pre_check_status": PreCheckStatus.ACADEMIC.value,
        "abstract": "Abstract content...",
        "created_at": "2026-02-06T00:00:00Z",
        "updated_at": "2026-02-06T00:00:00Z"
    }

    mocker.patch("app.services.editor_service.EditorService.get_academic_queue", return_value=[mock_manuscript])
    mocker.patch(
        "app.services.editor_service.EditorService.submit_academic_check",
        return_value={
            "id": MOCK_MANUSCRIPT_ID,
            "status": ManuscriptStatus.UNDER_REVIEW.value,
        },
    )

    # 1. Test List Academic Queue
    response = await client.get("/api/v1/editor/academic")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["pre_check_status"] == "academic"

    # 2. Test Submit Check (Decision: review)
    response = await client.post(f"/api/v1/editor/manuscripts/{MOCK_MANUSCRIPT_ID}/academic-check", json={"decision": "review"})
    assert response.status_code == 200
    assert response.json()["message"] == "Academic check submitted"


async def test_submit_academic_check_passes_actor_roles_to_service(client, mocker):
    submit_mock = mocker.patch(
        "app.services.editor_service.EditorService.submit_academic_check",
        return_value={
            "id": MOCK_MANUSCRIPT_ID,
            "status": ManuscriptStatus.UNDER_REVIEW.value,
        },
    )

    response = await client.post(
        f"/api/v1/editor/manuscripts/{MOCK_MANUSCRIPT_ID}/academic-check",
        json={"decision": "review"},
    )

    assert response.status_code == 200
    assert submit_mock.call_args.kwargs["actor_roles"] == ["admin", "managing_editor", "assistant_editor", "editor_in_chief"]


async def test_eic_final_decision_queue_flow(client, mocker):
    """
    EIC 终审队列接口集成校验。
    """
    mocker.patch("app.core.auth_utils.get_current_user", return_value={"id": MOCK_EIC_ID, "roles": ["editor_in_chief"]})
    mock_rows = [
        {
            "id": MOCK_MANUSCRIPT_ID,
            "title": "Decision Manuscript",
            "status": ManuscriptStatus.DECISION.value,
            "updated_at": "2026-02-11T00:00:00Z",
            "latest_first_decision_draft": {"decision": "minor_revision"},
        }
    ]
    mocker.patch("app.services.editor_service.EditorService.get_final_decision_queue", return_value=mock_rows)

    response = await client.get("/api/v1/editor/final-decision")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["status"] == "decision"
