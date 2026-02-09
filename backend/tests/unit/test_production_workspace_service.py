from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.models.production_workspace import CreateProductionCycleRequest, SubmitProofreadingRequest
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


def _svc() -> ProductionWorkspaceService:
    svc = ProductionWorkspaceService()
    svc.client = _NoopClient()  # type: ignore[assignment]
    return svc


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
            profile_roles=["editor"],
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
            profile_roles=["editor"],
            request=CreateProductionCycleRequest(
                layout_editor_id="00000000-0000-0000-0000-000000000001",
                proofreader_author_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                proof_due_at=datetime.now(timezone.utc) + timedelta(days=2),
            ),
        )
    assert exc.value.status_code == 422


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
            profile_roles=["editor"],
        )
    assert exc.value.status_code == 422


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
