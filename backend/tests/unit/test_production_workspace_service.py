from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.models.production_workspace import (
    CreateProductionCycleRequest,
    ProductionCyclePayload,
    SubmitProofreadingRequest,
)
from app.services.production_workspace_service import ProductionWorkspaceService


class _NoopClient:
    def table(self, _name: str):
        return self

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def execute(self):
        return SimpleNamespace(data=[])


class _UploadTable:
    def __init__(self, row: dict):
        self._row = row
        self._payload: dict | None = None

    def insert(self, payload: dict):
        self._payload = payload
        return self

    def update(self, payload: dict):
        self._payload = payload
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def execute(self):
        data = dict(self._row)
        data.update(self._payload or {})
        return SimpleNamespace(data=[data])


class _UploadBucket:
    def __init__(self):
        self.uploads: list[dict] = []
        self.removals: list[list[str]] = []

    def upload(self, path: str, content: bytes, options: dict):
        self.uploads.append({"path": path, "content": content, "options": options})

    def remove(self, paths: list[str]):
        self.removals.append(paths)


class _UploadStorage:
    def __init__(self):
        self.bucket = _UploadBucket()

    def from_(self, _name: str):
        return self.bucket


class _UploadClient:
    def __init__(self, row: dict):
        self._row = row
        self.storage = _UploadStorage()

    def table(self, _name: str):
        return _UploadTable(self._row)


def _svc() -> ProductionWorkspaceService:
    svc = ProductionWorkspaceService()
    svc.client = _NoopClient()  # type: ignore[assignment]
    return svc


class _SchemaErrorQuery:
    def __init__(self, responses: list[object]):
        self._responses = responses

    def select(self, *_args, **_kwargs):
        return self

    def insert(self, *_args, **_kwargs):
        return self

    def update(self, *_args, **_kwargs):
        return self

    def delete(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def in_(self, *_args, **_kwargs):
        return self

    def contains(self, *_args, **_kwargs):
        return self

    def or_(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def single(self, *_args, **_kwargs):
        return self

    def execute(self):
        if not self._responses:
            raise AssertionError("No schema error response queued")
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class _SchemaErrorClient:
    def __init__(self, responses_by_table: dict[str, list[object]]):
        self._responses_by_table = {name: list(items) for name, items in responses_by_table.items()}

    def table(self, name: str):
        return _SchemaErrorQuery(self._responses_by_table.setdefault(name, []))


class _SchemaErrorClientWithStorage(_SchemaErrorClient):
    def __init__(self, responses_by_table: dict[str, list[object]]):
        super().__init__(responses_by_table)
        self.storage = _UploadStorage()


def test_create_cycle_rejects_active_cycle(monkeypatch: pytest.MonkeyPatch):
    svc = _svc()

    monkeypatch.setattr(
        svc,
        "_get_manuscript",
        lambda _id: {
            "id": _id,
            "status": "approved",
            "author_id": "author-1",
            "editor_id": "editor-1",
            "owner_id": "",
        },
    )
    monkeypatch.setattr(svc, "_ensure_editor_access", lambda **_kwargs: None)
    monkeypatch.setattr(
        svc,
        "_get_cycles",
        lambda _id: [{"id": "cycle-1", "status": "awaiting_author", "cycle_no": 1}],
    )

    with pytest.raises(HTTPException) as exc:
        svc.create_cycle(
            manuscript_id="ms-1",
            user_id="editor-1",
            profile_roles=["managing_editor"],
            request=CreateProductionCycleRequest(
                layout_editor_id="00000000-0000-0000-0000-000000000001",
                proofreader_author_id="00000000-0000-0000-0000-000000000002",
                proof_due_at=datetime.now(timezone.utc) + timedelta(days=2),
            ),
        )
    assert exc.value.status_code == 409


def test_create_cycle_requires_mvp_author_binding(monkeypatch: pytest.MonkeyPatch):
    svc = _svc()

    monkeypatch.setattr(
        svc,
        "_get_manuscript",
        lambda _id: {
            "id": _id,
            "status": "approved",
            "author_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "editor_id": "editor-1",
            "owner_id": "",
        },
    )
    monkeypatch.setattr(svc, "_ensure_editor_access", lambda **_kwargs: None)
    monkeypatch.setattr(svc, "_get_cycles", lambda _id: [])

    with pytest.raises(HTTPException) as exc:
        svc.create_cycle(
            manuscript_id="ms-1",
            user_id="editor-1",
            profile_roles=["managing_editor"],
            request=CreateProductionCycleRequest(
                layout_editor_id="00000000-0000-0000-0000-000000000001",
                proofreader_author_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                proof_due_at=datetime.now(timezone.utc) + timedelta(days=2),
            ),
        )
    assert exc.value.status_code == 422


def test_create_cycle_rejects_missing_sop_columns_instead_of_legacy_fallback(monkeypatch: pytest.MonkeyPatch):
    svc = _svc()
    svc.client = _SchemaErrorClient(
        {
            "production_cycles": [
                RuntimeError('column "stage" does not exist'),
                SimpleNamespace(data=[{"id": "cycle-1", "status": "draft"}]),
            ]
        }
    )  # type: ignore[assignment]

    monkeypatch.setattr(
        svc,
        "_get_manuscript",
        lambda _id: {
            "id": _id,
            "status": "approved",
            "author_id": "00000000-0000-0000-0000-000000000002",
            "editor_id": "editor-1",
            "owner_id": "",
        },
    )
    monkeypatch.setattr(svc, "_ensure_editor_access", lambda **_kwargs: None)
    monkeypatch.setattr(svc, "_get_cycles", lambda _id: [])
    monkeypatch.setattr(svc, "_get_profile_roles", lambda _user_id: {"production_editor"})

    with pytest.raises(HTTPException) as exc:
        svc.create_cycle(
            manuscript_id="ms-1",
            user_id="editor-1",
            profile_roles=["managing_editor"],
            request=CreateProductionCycleRequest(
                layout_editor_id="00000000-0000-0000-0000-000000000001",
                proofreader_author_id="00000000-0000-0000-0000-000000000002",
                proof_due_at=datetime.now(timezone.utc) + timedelta(days=2),
            ),
        )

    assert exc.value.status_code == 503
    assert str(exc.value.detail).startswith("Production SOP schema not migrated:")


def test_update_assignments_rejects_missing_assignment_columns(monkeypatch: pytest.MonkeyPatch):
    svc = _svc()
    svc.client = _SchemaErrorClient(
        {
            "production_cycles": [
                RuntimeError('column "coordinator_ae_id" does not exist'),
            ]
        }
    )  # type: ignore[assignment]

    cycle = {
        "id": "cycle-1",
        "manuscript_id": "ms-1",
        "status": "draft",
        "stage": "received",
        "layout_editor_id": "editor-1",
        "proofreader_author_id": "author-1",
    }
    monkeypatch.setattr(svc, "_get_manuscript", lambda _id: {"id": _id, "status": "approved"})
    monkeypatch.setattr(svc, "_ensure_editor_access", lambda **_kwargs: None)
    monkeypatch.setattr(svc, "_get_cycle", lambda manuscript_id, cycle_id: dict(cycle))

    request = SimpleNamespace(
        coordinator_ae_id="editor-1",
        typesetter_id=None,
        language_editor_id=None,
        pdf_editor_id=None,
    )

    with pytest.raises(HTTPException) as exc:
        svc.update_assignments(
            manuscript_id="ms-1",
            cycle_id="cycle-1",
            user_id="editor-1",
            profile_roles=["managing_editor"],
            request=request,
        )

    assert exc.value.status_code == 503
    assert str(exc.value.detail).startswith("Production SOP schema not migrated:")


def test_transition_stage_rejects_missing_stage_column(monkeypatch: pytest.MonkeyPatch):
    svc = _svc()
    svc.client = _SchemaErrorClient(
        {
            "production_cycles": [
                RuntimeError('column "stage" does not exist'),
                SimpleNamespace(data=[{"id": "cycle-1", "status": "draft", "updated_at": datetime.now(timezone.utc).isoformat()}]),
            ]
        }
    )  # type: ignore[assignment]

    cycle = {
        "id": "cycle-1",
        "manuscript_id": "ms-1",
        "status": "draft",
        "stage": "received",
        "layout_editor_id": "editor-1",
        "proofreader_author_id": "author-1",
    }
    monkeypatch.setattr(svc, "_get_manuscript", lambda _id: {"id": _id, "status": "approved"})
    monkeypatch.setattr(svc, "_ensure_editor_access", lambda **_kwargs: None)
    monkeypatch.setattr(svc, "_get_cycle", lambda manuscript_id, cycle_id: dict(cycle))

    with pytest.raises(HTTPException) as exc:
        svc.transition_stage(
            manuscript_id="ms-1",
            cycle_id="cycle-1",
            user_id="editor-1",
            profile_roles=["production_editor"],
            target_stage="typesetting",
            comment=None,
        )

    assert exc.value.status_code == 503
    assert str(exc.value.detail).startswith("Production SOP schema not migrated:")


def test_assert_publish_gate_ready_rejects_missing_stage_column(monkeypatch: pytest.MonkeyPatch):
    svc = _svc()
    svc.client = _SchemaErrorClient(
        {
            "production_cycles": [
                RuntimeError('column "stage" does not exist'),
            ]
        }
    )  # type: ignore[assignment]

    with pytest.raises(HTTPException) as exc:
        svc.assert_publish_gate_ready(manuscript_id="ms-1")

    assert exc.value.status_code == 503
    assert str(exc.value.detail).startswith("Production SOP schema not migrated:")


@pytest.mark.parametrize("missing_column", ["approved_at", "galley_path"])
def test_assert_publish_gate_ready_rejects_other_required_columns(
    monkeypatch: pytest.MonkeyPatch,
    missing_column: str,
):
    svc = _svc()
    svc.client = _SchemaErrorClient(
        {
            "production_cycles": [
                RuntimeError(f'column "{missing_column}" does not exist'),
            ]
        }
    )  # type: ignore[assignment]

    with pytest.raises(HTTPException) as exc:
        svc.assert_publish_gate_ready(manuscript_id="ms-1")

    assert exc.value.status_code == 503
    assert str(exc.value.detail).startswith("Production SOP schema not migrated:")


def test_get_cycles_rejects_missing_sop_columns(monkeypatch: pytest.MonkeyPatch):
    svc = _svc()
    svc.client = _SchemaErrorClient(
        {
            "production_cycles": [
                RuntimeError('column "stage" does not exist'),
            ]
        }
    )  # type: ignore[assignment]

    with pytest.raises(HTTPException) as exc:
        svc._get_cycles("ms-1")

    assert exc.value.status_code == 503
    assert str(exc.value.detail).startswith("Production SOP schema not migrated:")


def test_get_cycle_artifacts_rejects_missing_table(monkeypatch: pytest.MonkeyPatch):
    svc = _svc()
    svc.client = _SchemaErrorClient(
        {
            "production_cycle_artifacts": [
                RuntimeError('Could not find the table "public.production_cycle_artifacts" in the schema cache'),
            ]
        }
    )  # type: ignore[assignment]

    with pytest.raises(HTTPException) as exc:
        svc._get_cycle_artifacts("cycle-1")

    assert exc.value.status_code == 503
    assert str(exc.value.detail).startswith("Production SOP schema not migrated:")


def test_list_my_queue_rejects_missing_sop_columns(monkeypatch: pytest.MonkeyPatch):
    svc = _svc()
    svc.client = _SchemaErrorClient(
        {
            "production_cycles": [
                RuntimeError('column "stage" does not exist'),
            ]
        }
    )  # type: ignore[assignment]

    with pytest.raises(HTTPException) as exc:
        svc.list_my_queue(user_id="editor-1", profile_roles=["production_editor"])

    assert exc.value.status_code == 503
    assert str(exc.value.detail).startswith("Production SOP schema not migrated:")


def test_upload_galley_rejects_missing_sop_columns(monkeypatch: pytest.MonkeyPatch):
    cycle_row = {
        "id": "cycle-1",
        "manuscript_id": "ms-1",
        "cycle_no": 1,
        "status": "draft",
        "proofreader_author_id": "author-1",
        "layout_editor_id": "editor-1",
    }
    svc = _svc()
    svc.client = _SchemaErrorClientWithStorage(
        {
            "production_cycle_artifacts": [SimpleNamespace(data=[{"id": "artifact-1"}])],
            "production_cycles": [RuntimeError('column "stage" does not exist')],
        }
    )  # type: ignore[assignment]

    monkeypatch.setattr(
        svc,
        "_get_manuscript",
        lambda _id: {
            "id": _id,
            "status": "english_editing",
            "title": "Demo Manuscript",
            "author_id": "author-1",
        },
    )
    monkeypatch.setattr(svc, "_get_cycle", lambda manuscript_id, cycle_id: dict(cycle_row))
    monkeypatch.setattr(svc, "_ensure_editor_access", lambda **_kwargs: None)
    monkeypatch.setattr(svc, "_ensure_bucket", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(svc, "_insert_log", lambda **_kwargs: None)
    monkeypatch.setattr(svc, "_notify", lambda **_kwargs: None)
    monkeypatch.setattr(svc, "_format_cycle", lambda row, include_signed_url: row)

    with pytest.raises(HTTPException) as exc:
        svc.upload_galley(
            manuscript_id="ms-1",
            cycle_id="cycle-1",
            user_id="editor-1",
            profile_roles=["production_editor"],
            filename="proof.pdf",
            content=b"%PDF-1.4 proof",
            version_note="v1",
            proof_due_at=datetime.now(timezone.utc) + timedelta(days=2),
            content_type="application/pdf",
        )

    assert exc.value.status_code == 503
    assert str(exc.value.detail).startswith("Production SOP schema not migrated:")


def test_submit_proofreading_rejects_missing_attachment_columns(monkeypatch: pytest.MonkeyPatch):
    svc = _svc()
    svc.client = _SchemaErrorClientWithStorage(
        {
            "production_cycle_artifacts": [SimpleNamespace(data=[{"id": "artifact-1"}])],
            "production_proofreading_responses": [RuntimeError('column "attachment_bucket" does not exist')],
        }
    )  # type: ignore[assignment]

    manuscript = {
        "id": "ms-1",
        "status": "proofreading",
        "author_id": "author-1",
        "editor_id": "editor-1",
        "owner_id": "",
        "title": "Demo",
    }
    cycle = {
        "id": "cycle-1",
        "manuscript_id": "ms-1",
        "status": "awaiting_author",
        "proofreader_author_id": "author-1",
        "proof_due_at": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
        "layout_editor_id": "editor-1",
        "coordinator_ae_id": "editor-1",
        "current_assignee_id": "author-1",
    }
    monkeypatch.setattr(svc, "_get_manuscript", lambda _id: manuscript)
    monkeypatch.setattr(svc, "_get_cycle", lambda manuscript_id, cycle_id: dict(cycle))
    monkeypatch.setattr(svc, "_ensure_author_or_internal_access", lambda **_kwargs: False)
    monkeypatch.setattr(svc, "_get_latest_response", lambda _cycle_id: None)
    monkeypatch.setattr(svc, "_ensure_bucket", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(svc, "_insert_log", lambda **_kwargs: None)
    monkeypatch.setattr(svc, "_notify", lambda **_kwargs: None)

    with pytest.raises(HTTPException) as exc:
        svc.submit_proofreading(
            manuscript_id="ms-1",
            cycle_id="cycle-1",
            user_id="author-1",
            profile_roles=["author"],
            request=SubmitProofreadingRequest(
                decision="submit_corrections",
                summary="Fixes attached",
                corrections=[{"suggested_text": "Fix typo"}],
            ),
            attachment_filename="annotated.pdf",
            attachment_content=b"%PDF-1.4 mock",
            attachment_content_type="application/pdf",
        )

    assert exc.value.status_code == 503
    assert str(exc.value.detail).startswith("Production SOP schema not migrated:")


def test_insert_log_rejects_missing_payload_column(monkeypatch: pytest.MonkeyPatch):
    svc = _svc()
    svc.client = _SchemaErrorClient(
        {
            "status_transition_logs": [
                RuntimeError('column "payload" does not exist'),
                SimpleNamespace(data=[{"id": "log-1"}]),
            ]
        }
    )  # type: ignore[assignment]

    with pytest.raises(HTTPException) as exc:
        svc._insert_log(
            manuscript_id="ms-1",
            from_status="approved_for_publish",
            to_status="published",
            changed_by="editor-1",
            comment="publish",
            payload={"cycle_id": "cycle-1", "event_type": "publish"},
        )

    assert exc.value.status_code == 503
    assert str(exc.value.detail).startswith("Production SOP schema not migrated:")


def test_insert_log_rejects_missing_production_cycle_events_table(monkeypatch: pytest.MonkeyPatch):
    svc = _svc()
    svc.client = _SchemaErrorClient(
        {
            "status_transition_logs": [SimpleNamespace(data=[{"id": "log-1"}])],
            "production_cycle_events": [
                RuntimeError('Could not find the table "public.production_cycle_events" in the schema cache (PGRST205)'),
            ],
        }
    )  # type: ignore[assignment]

    with pytest.raises(HTTPException) as exc:
        svc._insert_log(
            manuscript_id="ms-1",
            from_status="approved_for_publish",
            to_status="published",
            changed_by="editor-1",
            comment="publish",
            payload={"cycle_id": "cycle-1", "event_type": "publish"},
        )

    assert exc.value.status_code == 503
    assert str(exc.value.detail).startswith("Production SOP schema not migrated:")


def test_upload_artifact_rejects_missing_artifact_columns(monkeypatch: pytest.MonkeyPatch):
    cycle_row = {
        "id": "cycle-1",
        "manuscript_id": "ms-1",
        "cycle_no": 1,
        "status": "draft",
        "stage": "received",
        "proofreader_author_id": "author-1",
        "layout_editor_id": "editor-1",
    }
    svc = _svc()
    svc.client = _SchemaErrorClientWithStorage(
        {
            "production_cycle_artifacts": [RuntimeError('column "artifact_kind" does not exist')],
        }
    )  # type: ignore[assignment]

    monkeypatch.setattr(svc, "_get_manuscript", lambda _id: {"id": _id, "status": "approved"})
    monkeypatch.setattr(svc, "_get_cycle", lambda manuscript_id, cycle_id: dict(cycle_row))
    monkeypatch.setattr(svc, "_ensure_editor_access", lambda **_kwargs: None)
    monkeypatch.setattr(svc, "_ensure_bucket", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(svc, "_insert_log", lambda **_kwargs: None)
    monkeypatch.setattr(svc, "_format_cycle", lambda row, include_signed_url: row)

    with pytest.raises(HTTPException) as exc:
        svc.upload_artifact(
            manuscript_id="ms-1",
            cycle_id="cycle-1",
            user_id="editor-1",
            profile_roles=["production_editor"],
            artifact_kind="typeset_output",
            filename="typeset.pdf",
            content=b"%PDF-1.4 artifact",
            version_note="v1",
            content_type="application/pdf",
        )

    assert exc.value.status_code == 503
    assert str(exc.value.detail).startswith("Production SOP schema not migrated:")


def test_submit_proofreading_rejects_missing_correction_item_columns(monkeypatch: pytest.MonkeyPatch):
    svc = _svc()
    svc.client = _SchemaErrorClientWithStorage(
        {
            "production_proofreading_responses": [SimpleNamespace(data=[{"id": "resp-1"}])],
            "production_correction_items": [
                SimpleNamespace(data=[]),
                RuntimeError('column "suggested_text" does not exist'),
            ],
        }
    )  # type: ignore[assignment]

    manuscript = {
        "id": "ms-1",
        "status": "proofreading",
        "author_id": "author-1",
        "editor_id": "editor-1",
        "owner_id": "",
        "title": "Demo",
    }
    cycle = {
        "id": "cycle-1",
        "manuscript_id": "ms-1",
        "status": "awaiting_author",
        "proofreader_author_id": "author-1",
        "proof_due_at": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
        "layout_editor_id": "editor-1",
        "coordinator_ae_id": "editor-1",
        "current_assignee_id": "author-1",
    }
    monkeypatch.setattr(svc, "_get_manuscript", lambda _id: manuscript)
    monkeypatch.setattr(svc, "_get_cycle", lambda manuscript_id, cycle_id: dict(cycle))
    monkeypatch.setattr(svc, "_ensure_author_or_internal_access", lambda **_kwargs: False)
    monkeypatch.setattr(svc, "_get_latest_response", lambda _cycle_id: None)
    monkeypatch.setattr(svc, "_ensure_bucket", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(svc, "_insert_log", lambda **_kwargs: None)
    monkeypatch.setattr(svc, "_notify", lambda **_kwargs: None)

    with pytest.raises(HTTPException) as exc:
        svc.submit_proofreading(
            manuscript_id="ms-1",
            cycle_id="cycle-1",
            user_id="author-1",
            profile_roles=["author"],
            request=SubmitProofreadingRequest(
                decision="submit_corrections",
                summary="Fixes attached",
                corrections=[{"suggested_text": "Fix typo"}],
            ),
        )

    assert exc.value.status_code == 503
    assert str(exc.value.detail).startswith("Production SOP schema not migrated:")


def test_submit_proofreading_blocks_after_due(monkeypatch: pytest.MonkeyPatch):
    svc = _svc()

    monkeypatch.setattr(
        svc,
        "_get_manuscript",
        lambda _id: {
            "id": _id,
            "status": "proofreading",
            "author_id": "author-1",
            "editor_id": "editor-1",
            "owner_id": "",
            "title": "Demo",
        },
    )
    monkeypatch.setattr(
        svc,
        "_get_cycle",
        lambda manuscript_id, cycle_id: {
            "id": cycle_id,
            "manuscript_id": manuscript_id,
            "status": "awaiting_author",
            "proofreader_author_id": "author-1",
            "proof_due_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
            "layout_editor_id": "editor-1",
        },
    )
    monkeypatch.setattr(svc, "_ensure_author_or_internal_access", lambda **_kwargs: False)
    monkeypatch.setattr(svc, "_get_latest_response", lambda _cycle_id: None)

    with pytest.raises(HTTPException) as exc:
        svc.submit_proofreading(
            manuscript_id="ms-1",
            cycle_id="cycle-1",
            user_id="author-1",
            profile_roles=["author"],
            request=SubmitProofreadingRequest(decision="confirm_clean", summary="ok", corrections=[]),
        )
    assert exc.value.status_code == 422


def test_approve_cycle_requires_author_confirmed(monkeypatch: pytest.MonkeyPatch):
    svc = _svc()

    monkeypatch.setattr(
        svc,
        "_get_manuscript",
        lambda _id: {
            "id": _id,
            "status": "proofreading",
            "author_id": "author-1",
            "editor_id": "editor-1",
            "owner_id": "",
            "title": "Demo",
        },
    )
    monkeypatch.setattr(svc, "_ensure_editor_access", lambda **_kwargs: None)
    monkeypatch.setattr(
        svc,
        "_get_cycle",
        lambda manuscript_id, cycle_id: {
            "id": cycle_id,
            "manuscript_id": manuscript_id,
            "status": "awaiting_author",
            "galley_path": "production_cycles/ms-1/cycle-1/proof.pdf",
        },
    )

    with pytest.raises(HTTPException) as exc:
        svc.approve_cycle(
            manuscript_id="ms-1",
            cycle_id="cycle-1",
            user_id="editor-1",
            profile_roles=["managing_editor"],
        )
    assert exc.value.status_code == 422


def test_upload_galley_sends_initial_proofreading_email(monkeypatch: pytest.MonkeyPatch):
    cycle_row = {
        "id": "cycle-1",
        "manuscript_id": "ms-1",
        "cycle_no": 1,
        "status": "draft",
        "proofreader_author_id": "author-1",
        "layout_editor_id": "editor-1",
    }
    svc = _svc()
    svc.client = _UploadClient(cycle_row)  # type: ignore[assignment]

    monkeypatch.setattr(
        svc,
        "_get_manuscript",
        lambda _id: {
            "id": _id,
            "status": "english_editing",
            "title": "Demo Manuscript",
            "author_id": "author-1",
        },
    )
    monkeypatch.setattr(svc, "_get_cycle", lambda manuscript_id, cycle_id: dict(cycle_row))
    monkeypatch.setattr(svc, "_ensure_editor_access", lambda **_kwargs: None)
    monkeypatch.setattr(svc, "_ensure_bucket", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(svc, "_insert_log", lambda **_kwargs: None)
    monkeypatch.setattr(svc, "_notify", lambda **_kwargs: None)
    monkeypatch.setattr(svc, "_format_cycle", lambda row, include_signed_url: row)

    monkeypatch.setattr(
        "app.services.production_workspace_service_workflow_cycle_writes.resolve_author_notification_target",
        lambda **_kwargs: {
            "recipient_email": "corr@example.org",
            "recipient_name": "Corr Author",
            "to_recipients": ["corr@example.org"],
            "cc_recipients": ["co@example.org", "office@example.org"],
            "reply_to_recipients": ["office@example.org"],
        },
    )
    email_send_mock = SimpleNamespace(call_args=None)

    def _send_rendered_email(**kwargs):
        email_send_mock.call_args = kwargs
        return {"ok": True, "status": "sent", "provider_id": "proof_1", "error_message": None}

    monkeypatch.setattr(
        "app.services.production_workspace_service_workflow_cycle_writes.email_service.send_rendered_email",
        _send_rendered_email,
    )

    row = svc.upload_galley(
        manuscript_id="ms-1",
        cycle_id="cycle-1",
        user_id="editor-1",
        profile_roles=["production_editor"],
        filename="proof.pdf",
        content=b"%PDF-1.4 proof",
        version_note="v1",
        proof_due_at=datetime.now(timezone.utc) + timedelta(days=2),
        content_type="application/pdf",
    )

    assert row["status"] == "awaiting_author"
    assert email_send_mock.call_args is not None
    assert email_send_mock.call_args["to_emails"] == ["corr@example.org"]
    assert email_send_mock.call_args["cc_emails"] == ["co@example.org", "office@example.org"]
    assert email_send_mock.call_args["reply_to_emails"] == ["office@example.org"]
    assert email_send_mock.call_args["template_key"] == "proofreading_request"
    assert email_send_mock.call_args["idempotency_key"] == "proofreading-request/cycle-1/initial"
    assert email_send_mock.call_args["audit_context"]["delivery_mode"] == "auto"


def test_upload_galley_does_not_auto_send_proofreading_email_on_resubmission(monkeypatch: pytest.MonkeyPatch):
    cycle_row = {
        "id": "cycle-1",
        "manuscript_id": "ms-1",
        "cycle_no": 1,
        "status": "author_corrections_submitted",
        "proofreader_author_id": "author-1",
        "layout_editor_id": "editor-1",
    }
    svc = _svc()
    svc.client = _UploadClient(cycle_row)  # type: ignore[assignment]

    monkeypatch.setattr(
        svc,
        "_get_manuscript",
        lambda _id: {
            "id": _id,
            "status": "proofreading",
            "title": "Demo Manuscript",
            "author_id": "author-1",
        },
    )
    monkeypatch.setattr(svc, "_get_cycle", lambda manuscript_id, cycle_id: dict(cycle_row))
    monkeypatch.setattr(svc, "_ensure_editor_access", lambda **_kwargs: None)
    monkeypatch.setattr(svc, "_ensure_bucket", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(svc, "_insert_log", lambda **_kwargs: None)
    monkeypatch.setattr(svc, "_notify", lambda **_kwargs: None)
    monkeypatch.setattr(svc, "_format_cycle", lambda row, include_signed_url: row)

    send_calls: list[dict] = []
    monkeypatch.setattr(
        "app.services.production_workspace_service_workflow_cycle_writes.email_service.send_rendered_email",
        lambda **kwargs: send_calls.append(kwargs) or {"ok": True, "status": "sent"},
    )

    row = svc.upload_galley(
        manuscript_id="ms-1",
        cycle_id="cycle-1",
        user_id="editor-1",
        profile_roles=["production_editor"],
        filename="proof.pdf",
        content=b"%PDF-1.4 proof",
        version_note="v2",
        proof_due_at=datetime.now(timezone.utc) + timedelta(days=2),
        content_type="application/pdf",
    )

    assert row["status"] == "awaiting_author"
    assert send_calls == []


def test_assert_publish_gate_ready_strict_requires_approved_cycle(monkeypatch: pytest.MonkeyPatch):
    svc = _svc()
    monkeypatch.setenv("PRODUCTION_CYCLE_STRICT", "1")

    with pytest.raises(HTTPException) as exc:
        svc.assert_publish_gate_ready(manuscript_id="ms-1")
    assert exc.value.status_code == 403


def test_submit_proofreading_request_validation():
    with pytest.raises(ValueError):
        SubmitProofreadingRequest(decision="submit_corrections", corrections=[])

    with pytest.raises(ValueError):
        SubmitProofreadingRequest(
            decision="confirm_clean",
            corrections=[{"suggested_text": "Fix typo"}],
        )


def test_assistant_editor_cannot_read_production_workspace_after_accept() -> None:
    svc = _svc()

    with pytest.raises(HTTPException) as exc:
        svc._ensure_editor_access(
            manuscript={"id": "ms-1", "assistant_editor_id": "ae-1"},
            user_id="ae-1",
            roles={"assistant_editor"},
            purpose="read",
        )

    assert exc.value.status_code == 403


def test_assistant_editor_can_read_when_assigned_as_production_coordinator() -> None:
    svc = _svc()

    svc._ensure_editor_access(
        manuscript={"id": "ms-1", "assistant_editor_id": "ae-1"},
        user_id="ae-1",
        roles={"assistant_editor"},
        cycle={"id": "cycle-1", "coordinator_ae_id": "ae-1", "stage": "ae_final_review"},
        purpose="read",
    )


def test_production_editor_can_write_when_current_assignee_matches_sop_contract() -> None:
    svc = _svc()

    svc._ensure_editor_access(
        manuscript={"id": "ms-1"},
        user_id="pe-1",
        roles={"production_editor"},
        cycle={
            "id": "cycle-1",
            "stage": "typesetting",
            "typesetter_id": "pe-1",
            "current_assignee_id": "pe-1",
        },
        purpose="write",
    )


def test_production_editor_can_read_workspace_after_cycle_approved_for_publish(monkeypatch: pytest.MonkeyPatch) -> None:
    svc = _svc()

    manuscript_id = "ms-1"
    pe_id = "pe-1"
    cycle_id = "cycle-1"

    monkeypatch.setattr(
        svc,
        "_get_manuscript",
        lambda _id: {
            "id": _id,
            "status": "proofreading",
            "author_id": "author-1",
            "editor_id": "editor-1",
            "owner_id": "",
            "assistant_editor_id": None,
            "file_path": "manuscripts/ms-1/original.pdf",
        },
    )
    monkeypatch.setattr(
        svc,
        "_get_cycles",
        lambda _id: [
            {
                "id": cycle_id,
                "manuscript_id": manuscript_id,
                "cycle_no": 1,
                "status": "approved_for_publish",
                "layout_editor_id": pe_id,
                "collaborator_editor_ids": [],
                "proofreader_author_id": "author-1",
                "galley_bucket": "production-proofs",
                "galley_path": "production_cycles/ms-1/cycle-1/proof.pdf",
                "version_note": "v1",
                "proof_due_at": datetime.now(timezone.utc).isoformat(),
                "approved_by": "me-1",
                "approved_at": datetime.now(timezone.utc).isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        ],
    )

    ctx = svc.get_workspace_context(
        manuscript_id=manuscript_id,
        user_id=pe_id,
        profile_roles=["production_editor"],
    )

    assert ctx["active_cycle"] is not None
    assert ctx["active_cycle"]["id"] == cycle_id
    assert ctx["active_cycle"]["status"] == "approved_for_publish"
    assert ctx["permissions"]["can_upload_galley"] is False
    assert ctx["permissions"]["can_approve"] is False


def test_production_cycle_payload_exposes_sop_contract_fields() -> None:
    cycle = ProductionCyclePayload(
        id="cycle-1",
        manuscript_id="ms-1",
        cycle_no=1,
        status="draft",
        stage="typesetting",
        layout_editor_id="layout-1",
        proofreader_author_id="author-1",
        coordinator_ae_id="ae-1",
        typesetter_id="typesetter-1",
        language_editor_id="lang-1",
        pdf_editor_id="pdf-1",
        current_assignee_id="typesetter-1",
        artifacts=[
            {
                "id": "artifact-1",
                "artifact_kind": "typeset_output",
                "storage_path": "production_cycles/ms-1/cycle-1/typeset.pdf",
            }
        ],
    )

    dumped = cycle.model_dump()

    assert dumped["stage"] == "typesetting"
    assert dumped["coordinator_ae_id"] == "ae-1"
    assert dumped["typesetter_id"] == "typesetter-1"
    assert dumped["language_editor_id"] == "lang-1"
    assert dumped["pdf_editor_id"] == "pdf-1"
    assert dumped["current_assignee_id"] == "typesetter-1"
    assert dumped["artifacts"][0]["artifact_kind"] == "typeset_output"


def test_production_cycle_payload_defaults_stage_from_legacy_status() -> None:
    cycle = ProductionCyclePayload(
        id="cycle-2",
        manuscript_id="ms-1",
        cycle_no=2,
        status="awaiting_author",
        layout_editor_id="layout-1",
        proofreader_author_id="author-1",
    )

    assert cycle.stage == "author_proofreading"
