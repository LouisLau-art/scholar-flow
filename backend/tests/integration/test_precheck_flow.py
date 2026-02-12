import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from app.models.manuscript import ManuscriptStatus, PreCheckStatus

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

from app.core.auth_utils import get_current_user
from app.core.roles import get_current_profile
from main import app

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
