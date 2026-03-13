from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import BackgroundTasks

from app.api.v1.editor_common import IntakeRevisionRequest, resolve_author_notification_target
from app.api.v1.editor_decision import request_revision as decision_request_revision
from app.api.v1.editor_heavy_decision import submit_final_decision_impl
from app.api.v1.editor_heavy_publish import publish_manuscript_dev_impl
from app.api.v1.editor_heavy_revision import request_revision_impl
from app.api.v1.editor_precheck import submit_intake_revision


class _Resp:
    def __init__(self, data=None, error=None):
        self.data = data
        self.error = error


def _make_chain_mock(responses):
    mock = MagicMock()
    normalized = [_Resp(data=item) if not isinstance(item, _Resp) else item for item in responses]
    for name in ("table", "select", "eq", "single", "update", "upsert", "limit", "insert", "delete", "order"):
        getattr(mock, name).return_value = mock
    mock.execute.side_effect = normalized
    return mock


class _FakeEditorService:
    def __init__(self, updated):
        self.updated = updated

    def request_intake_revision(self, **_kwargs):
        return self.updated


class _FakeRevisionService:
    def __init__(self, manuscript):
        self.manuscript = manuscript

    def create_revision_request(self, **_kwargs):
        revision_id = str(uuid4())
        return {
            "success": True,
            "data": {
                "revision": {
                    "id": revision_id,
                    "manuscript_id": self.manuscript["id"],
                    "round_number": 1,
                    "decision_type": "minor",
                    "editor_comment": "Please revise",
                    "created_at": "2026-03-11T00:00:00+00:00",
                }
            },
        }

    def get_manuscript(self, _manuscript_id):
        return self.manuscript


def _normalize_target(email: str, name: str):
    return {
        "recipient_email": email,
        "recipient_name": name,
        "corresponding_author": {"name": name, "email": email, "is_corresponding": True},
        "source": "corresponding_author_email",
        "to_recipients": [email],
        "cc_recipients": ["coauthor@example.org", "office@example.org"],
        "bcc_recipients": [],
        "reply_to_recipients": ["office@example.org"],
        "author_profile": None,
    }


def test_resolve_author_notification_target_prefers_corresponding_author_email_and_ccs_other_authors():
    manuscript = {
        "submission_email": "Submissions@Example.org ",
        "author_contacts": [
            {
                "name": "Dr. Alice Author",
                "email": "corr@example.org",
                "affiliation": "Example U",
                "is_corresponding": True,
            },
            {
                "name": "Bob Author",
                "email": "bob@example.org",
                "affiliation": "Example I",
                "is_corresponding": False,
            },
        ],
    }

    target = resolve_author_notification_target(manuscript=manuscript)

    assert target["recipient_email"] == "corr@example.org"
    assert target["recipient_name"] == "Dr. Alice Author"
    assert target["source"] == "corresponding_author_email"
    assert target["to_recipients"] == ["corr@example.org"]
    assert target["cc_recipients"] == ["bob@example.org"]


def test_resolve_author_notification_target_includes_all_corresponding_authors_in_to():
    manuscript = {
        "submission_email": "submission@example.org",
        "author_contacts": [
            {
                "name": "Corr Author One",
                "email": "corr1@example.org",
                "affiliation": "Example U",
                "is_corresponding": True,
            },
            {
                "name": "Corr Author Two",
                "email": "corr2@example.org",
                "affiliation": "Example U",
                "is_corresponding": True,
            },
            {
                "name": "Co Author",
                "email": "co@example.org",
                "affiliation": "Example U",
                "is_corresponding": False,
            },
        ],
    }
    target = resolve_author_notification_target(
        manuscript=manuscript,
        author_profile={"email": "account@example.org", "full_name": "Account Author"},
    )

    assert target["recipient_email"] == "corr1@example.org"
    assert target["recipient_name"] == "Corr Author One"
    assert target["source"] == "corresponding_author_email"
    assert target["to_recipients"] == ["corr1@example.org", "corr2@example.org"]
    assert target["cc_recipients"] == ["co@example.org"]


def test_resolve_author_notification_target_prefers_submission_email_over_non_corresponding_contacts():
    manuscript = {
        "submission_email": "delegate@example.org",
        "author_contacts": [
            {
                "name": "Lead Author",
                "email": "lead.author@example.org",
                "affiliation": "Example U",
                "is_corresponding": False,
            },
            {
                "name": "Second Author",
                "email": "second.author@example.org",
                "affiliation": "Example U",
                "is_corresponding": False,
            },
        ],
    }

    target = resolve_author_notification_target(manuscript=manuscript)

    assert target["recipient_email"] == "delegate@example.org"
    assert target["source"] == "submission_email"
    assert target["to_recipients"] == ["delegate@example.org"]
    assert target["cc_recipients"] == ["lead.author@example.org", "second.author@example.org"]


def test_resolve_author_notification_target_falls_back_to_profile_email_when_submission_fields_missing():
    target = resolve_author_notification_target(
        manuscript={"author_contacts": []},
        author_profile={"email": "Author.Profile@Example.org", "full_name": "Profile Author"},
    )

    assert target["recipient_email"] == "author.profile@example.org"
    assert target["recipient_name"] == "Profile Author"
    assert target["source"] == "author_profile_email"
    assert target["to_recipients"] == ["author.profile@example.org"]


@pytest.mark.asyncio
async def test_submit_intake_revision_keeps_author_notification_in_app_only(monkeypatch):
    manuscript_id = uuid4()
    updated = {
        "id": str(manuscript_id),
        "author_id": str(uuid4()),
        "title": "Intake Revision Manuscript",
        "submission_email": "submission@example.org",
        "author_contacts": [],
    }
    background_tasks = BackgroundTasks()

    monkeypatch.setattr("app.api.v1.editor_precheck.ensure_manuscript_scope_access", lambda **_kwargs: None)
    monkeypatch.setattr("app.api.v1.editor_precheck.EditorService", lambda: _FakeEditorService(updated))
    with patch("app.api.v1.editor_precheck.NotificationService.create_notification", return_value=None), patch(
        "app.api.v1.editor_precheck.resolve_author_notification_target",
        return_value=_normalize_target("submission@example.org", "Corr Author"),
    ) as resolve_target_mock:
        result = await submit_intake_revision(
            id=manuscript_id,
            request=IntakeRevisionRequest(comment="Please update formatting."),
            background_tasks=background_tasks,
            current_user={"id": str(uuid4())},
            profile={"roles": ["managing_editor"]},
        )

    assert result["message"] == "Intake revision submitted"
    resolve_target_mock.assert_not_called()
    assert len(background_tasks.tasks) == 0


@pytest.mark.asyncio
async def test_request_revision_impl_keeps_author_notification_in_app_only(monkeypatch):
    manuscript = {
        "id": str(uuid4()),
        "author_id": str(uuid4()),
        "title": "Revision Manuscript",
        "submission_email": "submission@example.org",
        "author_contacts": [],
    }
    background_tasks = BackgroundTasks()
    request = SimpleNamespace(manuscript_id=manuscript["id"], decision_type="minor", comment="Please revise")

    monkeypatch.setattr("app.api.v1.editor_heavy_revision.RevisionService", lambda: _FakeRevisionService(manuscript))
    with patch("app.api.v1.editor_heavy_revision.NotificationService.create_notification", return_value=None), patch(
        "app.api.v1.editor_heavy_revision.resolve_author_notification_target",
        return_value=_normalize_target("submission@example.org", "Corr Author"),
    ) as resolve_target_mock:
        result = await request_revision_impl(
            request=request,
            profile={"roles": ["managing_editor"]},
            background_tasks=background_tasks,
            supabase_admin_client=MagicMock(),
        )

    assert str(result["data"]["revision"]["id"])
    resolve_target_mock.assert_not_called()
    assert len(background_tasks.tasks) == 0


@pytest.mark.asyncio
async def test_editor_decision_request_revision_preserves_author_email_envelope(monkeypatch):
    manuscript = {
        "id": str(uuid4()),
        "author_id": str(uuid4()),
        "title": "Decision Revision Manuscript",
        "submission_email": "submission@example.org",
        "author_contacts": [],
    }
    background_tasks = BackgroundTasks()
    request = SimpleNamespace(
        manuscript_id=manuscript["id"],
        decision_type="minor",
        comment="Please revise",
    )

    monkeypatch.setattr("app.api.v1.editor_decision.RevisionService", lambda: _FakeRevisionService(manuscript))
    with patch("app.api.v1.editor_decision.NotificationService.create_notification", return_value=None), patch(
        "app.api.v1.editor_decision.resolve_author_notification_target",
        return_value=_normalize_target("submission@example.org", "Corr Author"),
    ):
        result = await decision_request_revision(
            request=request,
            current_user={"id": str(uuid4())},
            profile={"roles": ["managing_editor"]},
            background_tasks=background_tasks,
        )

    assert str(result.data.id)
    assert len(background_tasks.tasks) == 1
    task = background_tasks.tasks[0]
    assert task.kwargs["to_email"] == "submission@example.org"
    assert task.kwargs["cc_emails"] == ["coauthor@example.org", "office@example.org"]
    assert task.kwargs["reply_to_emails"] == ["office@example.org"]


@pytest.mark.asyncio
async def test_submit_final_decision_impl_uses_resolved_author_target_for_decision_and_invoice(monkeypatch):
    manuscript_id = str(uuid4())
    background_tasks = BackgroundTasks()
    supabase = _make_chain_mock(
        [
            {"status": "decision"},
            [{"id": manuscript_id}],
            [{"id": str(uuid4())}],
            [],
            {"author_id": str(uuid4()), "title": "Decision Manuscript", "submission_email": "submission@example.org", "author_contacts": []},
            [],
        ]
    )

    with patch("app.api.v1.editor_heavy_decision.NotificationService.create_notification", return_value=None), patch(
        "app.api.v1.editor_heavy_decision.resolve_author_notification_target",
        return_value=_normalize_target("submission@example.org", "Corr Author"),
    ):
        result = await submit_final_decision_impl(
            background_tasks=background_tasks,
            current_user={"id": str(uuid4())},
            profile={"roles": ["admin"]},
            manuscript_id=manuscript_id,
            decision="accept",
            comment="Looks good",
            apc_amount=1000.0,
            supabase_admin_client=supabase,
            extract_error_fn=lambda response: getattr(response, "error", None),
            extract_data_fn=lambda response: getattr(response, "data", None),
            is_missing_column_error_fn=lambda _text: False,
            require_action_or_403_fn=lambda **_kwargs: None,
            ensure_manuscript_scope_access_fn=lambda **_kwargs: None,
        )

    assert result["success"] is True
    assert len(background_tasks.tasks) == 2
    invoice_pdf_task = background_tasks.tasks[0]
    decision_task = background_tasks.tasks[1]
    assert decision_task.kwargs["to_emails"] == ["submission@example.org"]
    assert decision_task.kwargs["cc_emails"] == ["coauthor@example.org", "office@example.org"]
    assert decision_task.kwargs["reply_to_emails"] == ["office@example.org"]
    assert decision_task.kwargs["template_key"] == "status_update"
    assert "Corr Author" in decision_task.kwargs["html_body"]
    assert invoice_pdf_task.func.__name__ == "generate_and_store_invoice_pdf_safe"


@pytest.mark.asyncio
async def test_publish_manuscript_dev_impl_uses_resolved_author_notification_target(monkeypatch):
    manuscript_id = str(uuid4())
    background_tasks = BackgroundTasks()
    supabase = _make_chain_mock(
        [
            {"status": "approved"},
            [],
            {"author_id": str(uuid4()), "title": "Published Manuscript", "submission_email": "submission@example.org", "author_contacts": []},
        ]
    )

    with patch("app.api.v1.editor_heavy_publish.NotificationService.create_notification", return_value=None), patch(
        "app.api.v1.editor_heavy_publish.resolve_author_notification_target",
        return_value=_normalize_target("submission@example.org", "Corr Author"),
    ):
        result = await publish_manuscript_dev_impl(
            background_tasks=background_tasks,
            current_user={"id": str(uuid4())},
            manuscript_id=manuscript_id,
            supabase_admin_client=supabase,
            publish_manuscript_fn=lambda manuscript_id: {"id": manuscript_id, "doi": "10.1234/test"},
        )

    assert result["success"] is True
    assert len(background_tasks.tasks) == 1
    task = background_tasks.tasks[0]
    assert task.kwargs["to_emails"] == ["submission@example.org"]
    assert task.kwargs["cc_emails"] == ["coauthor@example.org", "office@example.org"]
    assert task.kwargs["reply_to_emails"] == ["office@example.org"]
    assert task.kwargs["template_key"] == "published"
    assert "Corr Author" in task.kwargs["html_body"]
