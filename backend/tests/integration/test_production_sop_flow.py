from __future__ import annotations
import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from .test_utils import insert_manuscript, make_user
from .test_production_workspace_api import _require_schema

def _ensure_profile(db, *, user_id: str, email: str, roles: list[str]) -> None:
    db.table("user_profiles").upsert(
        {
            "id": user_id,
            "email": email,
            "roles": roles,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
        on_conflict="id",
    ).execute()


def _cleanup(db, manuscript_id: str, *, user_ids: list[str]) -> None:
    tables = [
        ("production_cycle_events", "manuscript_id", manuscript_id),
        ("production_cycle_artifacts", "manuscript_id", manuscript_id),
        ("production_proofreading_responses", "manuscript_id", manuscript_id),
        ("production_cycles", "manuscript_id", manuscript_id),
        ("status_transition_logs", "manuscript_id", manuscript_id),
        ("notifications", "manuscript_id", manuscript_id),
        ("invoices", "manuscript_id", manuscript_id),
        ("manuscripts", "id", manuscript_id),
    ]
    for table, column, value in tables:
        try:
            q = db.table(table).delete()
            if value is not None:
                q = q.eq(column, value)
            q.execute()
        except Exception:
            pass

    for uid in user_ids:
        try:
            db.table("user_profiles").delete().eq("id", uid).execute()
        except Exception:
            pass


@pytest.fixture
def test_data(supabase_admin_client, set_admin_emails):
    _require_schema(supabase_admin_client)
    editor = make_user(email="sop_editor@example.com")
    author = make_user(email="sop_author@example.com")
    set_admin_emails([editor.email])

    manuscript_id = str(uuid4())
    insert_manuscript(
        supabase_admin_client,
        manuscript_id=manuscript_id,
        author_id=author.id,
        status="approved",
        title="SOP Test Manuscript",
    )
    _ensure_profile(supabase_admin_client, user_id=editor.id, email=editor.email, roles=["admin", "editor", "production_editor", "assistant_editor"])
    _ensure_profile(supabase_admin_client, user_id=author.id, email=author.email, roles=["author"])
    
    yield {"editor": editor, "author": author, "manuscript_id": manuscript_id}
    
    _cleanup(supabase_admin_client, manuscript_id, user_ids=[editor.id, author.id])


@pytest.mark.integration
@pytest.mark.asyncio
async def test_production_sop_assignments_patch(client, test_data, supabase_admin_client):
    editor = test_data["editor"]
    author = test_data["author"]
    manuscript_id = test_data["manuscript_id"]
    
    # Create a cycle first
    due = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    create_res = await client.post(
        f"/api/v1/editor/manuscripts/{manuscript_id}/production-cycles",
        headers={"Authorization": f"Bearer {editor.token}"},
        json={
            "layout_editor_id": editor.id,
            "proofreader_author_id": author.id,
            "proof_due_at": due,
        },
    )
    assert create_res.status_code == 201
    cycle_id = create_res.json()["data"]["cycle"]["id"]
    
    # Test PATCH assignments
    patch_res = await client.patch(
        f"/api/v1/editor/manuscripts/{manuscript_id}/production-cycles/{cycle_id}/assignments",
        headers={"Authorization": f"Bearer {editor.token}"},
        json={
            "coordinator_ae_id": editor.id,
            "typesetter_id": editor.id,
        }
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["data"]["cycle"]["coordinator_ae_id"] == editor.id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_production_sop_artifacts_upload(client, test_data, supabase_admin_client):
    editor = test_data["editor"]
    author = test_data["author"]
    manuscript_id = test_data["manuscript_id"]
    
    create_res = await client.post(
        f"/api/v1/editor/manuscripts/{manuscript_id}/production-cycles",
        headers={"Authorization": f"Bearer {editor.token}"},
        json={"layout_editor_id": editor.id, "proofreader_author_id": author.id, "proof_due_at": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()},
    )
    cycle_id = create_res.json()["data"]["cycle"]["id"]
    
    # Upload artifact
    upload_res = await client.post(
        f"/api/v1/editor/manuscripts/{manuscript_id}/production-cycles/{cycle_id}/artifacts",
        headers={"Authorization": f"Bearer {editor.token}"},
        data={"artifact_kind": "typeset_output", "version_note": "first draft"},
        files={"file": ("typeset.pdf", b"%PDF-1.4 mock", "application/pdf")},
    )
    assert upload_res.status_code == 200
    assert upload_res.json()["data"]["artifact"]["artifact_kind"] == "typeset_output"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_production_sop_transitions(client, test_data, supabase_admin_client):
    editor = test_data["editor"]
    author = test_data["author"]
    manuscript_id = test_data["manuscript_id"]
    
    create_res = await client.post(
        f"/api/v1/editor/manuscripts/{manuscript_id}/production-cycles",
        headers={"Authorization": f"Bearer {editor.token}"},
        json={"layout_editor_id": editor.id, "proofreader_author_id": author.id, "proof_due_at": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()},
    )
    cycle_id = create_res.json()["data"]["cycle"]["id"]
    
    # Transition
    trans_res = await client.post(
        f"/api/v1/editor/manuscripts/{manuscript_id}/production-cycles/{cycle_id}/transitions",
        headers={"Authorization": f"Bearer {editor.token}"},
        json={"target_stage": "typesetting"}
    )
    assert trans_res.status_code == 200
    assert trans_res.json()["data"]["cycle"]["stage"] == "typesetting"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_production_sop_author_feedback(client, test_data, supabase_admin_client):
    editor = test_data["editor"]
    author = test_data["author"]
    manuscript_id = test_data["manuscript_id"]
    
    create_res = await client.post(
        f"/api/v1/editor/manuscripts/{manuscript_id}/production-cycles",
        headers={"Authorization": f"Bearer {editor.token}"},
        json={"layout_editor_id": editor.id, "proofreader_author_id": author.id, "proof_due_at": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()},
    )
    cycle_id = create_res.json()["data"]["cycle"]["id"]
    
    # Move to author_proofreading
    supabase_admin_client.table("production_cycles").update({"stage": "author_proofreading", "status": "awaiting_author"}).eq("id", cycle_id).execute()
    
    # Author submit feedback
    feedback_res = await client.post(
        f"/api/v1/manuscripts/{manuscript_id}/production-cycles/{cycle_id}/author-feedback",
        headers={"Authorization": f"Bearer {author.token}"},
        data={"decision": "submit_corrections", "summary": "Fixes attached"},
        files={"attachment": ("annotated.pdf", b"%PDF-1.4 mock", "application/pdf")},
    )
    assert feedback_res.status_code == 200
    assert feedback_res.json()["data"]["response"]["decision"] == "submit_corrections"
    assert feedback_res.json()["data"]["response"]["attachment_file_name"] == "annotated.pdf"
