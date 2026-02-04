from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import app.services.revision_service as revision_service_module


class _Resp:
    def __init__(self, *, data=None, error=None):
        self.data = data
        self.error = error


def _chain():
    q = MagicMock()
    for method in (
        "select",
        "eq",
        "single",
        "order",
        "limit",
        "insert",
        "update",
        "range",
    ):
        getattr(q, method).return_value = q
    return q


@pytest.fixture
def supabase_admin(monkeypatch):
    client = MagicMock()
    tables: dict[str, MagicMock] = {}

    def _table(name: str):
        tables.setdefault(name, _chain())
        return tables[name]

    client.table.side_effect = _table
    client._tables = tables  # type: ignore[attr-defined]
    monkeypatch.setattr(revision_service_module, "supabase_admin", client)
    return client


def test_extract_helpers_support_multiple_shapes(supabase_admin):
    svc = revision_service_module.RevisionService()

    assert svc._extract_data(None) is None
    assert svc._extract_data(_Resp(data={"id": 1})) == {"id": 1}
    assert svc._extract_data((None, [{"id": 2}])) == [{"id": 2}]
    assert svc._extract_data(object()) is None

    assert svc._extract_error(None) is None
    assert svc._extract_error(_Resp(error="boom")) == "boom"
    assert svc._extract_error(("err", [])) == "err"
    assert svc._extract_error(object()) is None


def test_get_manuscript_and_pending_revision_handle_exceptions(supabase_admin):
    svc = revision_service_module.RevisionService()

    manuscripts = supabase_admin._tables.setdefault("manuscripts", _chain())  # type: ignore[attr-defined]
    manuscripts.execute.side_effect = RuntimeError("db down")
    assert svc.get_manuscript("m1") is None

    revisions = supabase_admin._tables.setdefault("revisions", _chain())  # type: ignore[attr-defined]
    revisions.execute.side_effect = RuntimeError("db down")
    assert svc.get_pending_revision("m1") is None


def test_get_next_round_number_branches(supabase_admin):
    svc = revision_service_module.RevisionService()
    revisions = supabase_admin.table("revisions")

    revisions.execute.return_value = _Resp(data=[])
    assert svc.get_next_round_number("m1") == 1

    revisions.execute.return_value = _Resp(data=[{"round_number": 2}])
    assert svc.get_next_round_number("m1") == 3

    revisions.execute.side_effect = RuntimeError("db down")
    assert svc.get_next_round_number("m1") == 1


def test_create_revision_request_error_paths(supabase_admin, monkeypatch):
    svc = revision_service_module.RevisionService()

    monkeypatch.setattr(svc, "get_manuscript", lambda *_args, **_kwargs: None)
    assert svc.create_revision_request("m1", "major", "c")["success"] is False

    monkeypatch.setattr(
        svc,
        "get_manuscript",
        lambda *_args, **_kwargs: {"id": "m1", "status": "pre_check", "version": 1},
    )
    out = svc.create_revision_request("m1", "major", "c")
    assert out["success"] is False
    assert "Cannot request revision" in out["error"]


def test_create_revision_request_insert_and_update_failures(supabase_admin, monkeypatch):
    svc = revision_service_module.RevisionService()
    monkeypatch.setattr(
        svc,
        "get_manuscript",
        lambda *_args, **_kwargs: {"id": "m1", "status": "under_review", "version": 1},
    )
    monkeypatch.setattr(svc, "get_next_round_number", lambda *_args, **_kwargs: 1)

    # Snapshot insert can fail but must not fail the whole request.
    manuscript_versions = supabase_admin.table("manuscript_versions")
    manuscript_versions.execute.side_effect = RuntimeError("unique conflict")

    revisions = supabase_admin.table("revisions")
    revisions.execute.side_effect = RuntimeError("insert failed")
    out = svc.create_revision_request("m1", "minor", "c")
    assert out["success"] is False
    assert "Failed to create revision" in out["error"]

    # Insert ok, update manuscript fails.
    revisions.execute.side_effect = None
    revisions.execute.return_value = _Resp(data=[{"id": "r1"}])
    manuscripts = supabase_admin.table("manuscripts")
    manuscripts.execute.side_effect = RuntimeError("update failed")
    out = svc.create_revision_request("m1", "minor", "c")
    assert out["success"] is False
    assert "Failed to update manuscript status" in out["error"]


@pytest.mark.parametrize(
    "manuscript,pending,expected_error",
    [
        (None, None, "Manuscript not found"),
        ({"id": "m1", "status": "pre_check", "author_id": "a1", "version": 1}, None, "Cannot submit revision"),
        ({"id": "m1", "status": "minor_revision", "author_id": "a1", "version": 1}, None, "No pending revision request found"),
        (
            {"id": "m1", "status": "minor_revision", "author_id": "a1", "version": 1},
            {"id": "r1"},
            "Only the manuscript author can submit revisions",
        ),
    ],
)
def test_submit_revision_early_guards(supabase_admin, monkeypatch, manuscript, pending, expected_error):
    svc = revision_service_module.RevisionService()

    monkeypatch.setattr(svc, "get_manuscript", lambda *_args, **_kwargs: manuscript)
    monkeypatch.setattr(svc, "get_pending_revision", lambda *_args, **_kwargs: pending)

    author_id = "a1"
    if expected_error == "Only the manuscript author can submit revisions":
        author_id = "someone-else"

    out = svc.submit_revision(
        "m1",
        author_id,
        "m1/v2_file.pdf",
        "response",
    )
    assert out["success"] is False
    assert expected_error in out["error"]


def test_submit_revision_happy_path_and_failures(supabase_admin, monkeypatch):
    svc = revision_service_module.RevisionService()
    monkeypatch.setattr(
        svc,
        "get_manuscript",
        lambda *_args, **_kwargs: {
            "id": "m1",
            "status": "minor_revision",
            "author_id": "a1",
            "version": 1,
            "title": "t",
            "abstract": "a",
        },
    )
    monkeypatch.setattr(svc, "get_pending_revision", lambda *_args, **_kwargs: {"id": "r1"})

    manuscript_versions = supabase_admin.table("manuscript_versions")
    revisions = supabase_admin.table("revisions")
    manuscripts = supabase_admin.table("manuscripts")

    # Version insert fails.
    manuscript_versions.execute.side_effect = RuntimeError("insert failed")
    out = svc.submit_revision("m1", "a1", "m1/v2.pdf", "resp")
    assert out["success"] is False
    assert "Failed to create version" in out["error"]

    # Revision update fails.
    manuscript_versions.execute.side_effect = None
    manuscript_versions.execute.return_value = _Resp(data=[{"id": "v2"}])
    revisions.execute.side_effect = RuntimeError("update failed")
    out = svc.submit_revision("m1", "a1", "m1/v2.pdf", "resp")
    assert out["success"] is False
    assert "Failed to update revision" in out["error"]

    # Manuscript update fails.
    revisions.execute.side_effect = None
    revisions.execute.return_value = _Resp(data=[{"id": "r1"}])
    manuscripts.execute.side_effect = RuntimeError("update manuscript failed")
    out = svc.submit_revision("m1", "a1", "m1/v2.pdf", "resp", new_title="nt")
    assert out["success"] is False
    assert "Failed to update manuscript" in out["error"]

    # Full success.
    manuscripts.execute.side_effect = None
    manuscripts.execute.return_value = _Resp(data=[{"id": "m1"}])
    out = svc.submit_revision("m1", "a1", "m1/v2.pdf", "resp", new_abstract="na")
    assert out["success"] is True
    assert out["data"]["manuscript_status"] == "resubmitted"


def test_get_version_history_success_and_error(supabase_admin):
    svc = revision_service_module.RevisionService()

    manuscript_versions = supabase_admin.table("manuscript_versions")
    revisions = supabase_admin.table("revisions")

    manuscript_versions.execute.return_value = _Resp(data=[{"version_number": 1}])
    revisions.execute.return_value = _Resp(data=[{"round_number": 1}])
    out = svc.get_version_history("m1")
    assert out["success"] is True
    assert out["data"]["versions"][0]["version_number"] == 1

    manuscript_versions.execute.side_effect = RuntimeError("db down")
    out = svc.get_version_history("m1")
    assert out["success"] is False


def test_generate_versioned_file_path():
    svc = revision_service_module.RevisionService()
    assert svc.generate_versioned_file_path("m1", "paper.pdf", 2) == "m1/v2_paper.pdf"
