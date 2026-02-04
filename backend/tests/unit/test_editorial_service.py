from unittest.mock import MagicMock

import pytest

import app.services.editorial_service as editorial_service_module


class _Resp:
    def __init__(self, *, data=None, error=None):
        self.data = data
        self.error = error


def _chain():
    q = MagicMock()
    for method in ("select", "eq", "single", "execute", "update", "insert", "in_"):
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
    monkeypatch.setattr(editorial_service_module, "supabase_admin", client)
    return client


def test_update_status_rejects_invalid_status(supabase_admin):
    svc = editorial_service_module.EditorialService()
    with pytest.raises(Exception):
        svc.update_status(manuscript_id="m1", to_status="not-a-status", changed_by="u1")


def test_update_status_valid_transition_writes_log(supabase_admin):
    svc = editorial_service_module.EditorialService()

    manuscripts = supabase_admin.table("manuscripts")
    manuscripts.execute.side_effect = [
        _Resp(data={"id": "m1", "status": "pre_check"}),  # get_manuscript
        _Resp(data=[{"id": "m1", "status": "under_review"}]),  # update
    ]

    logs = supabase_admin.table("status_transition_logs")
    logs.execute.return_value = _Resp(data=[{"id": "l1"}])

    out = svc.update_status(manuscript_id="m1", to_status="under_review", changed_by="u1")
    assert out["status"] == "under_review"
    assert logs.insert.called is True


def test_update_status_blocks_skip_when_not_admin(supabase_admin):
    svc = editorial_service_module.EditorialService()

    manuscripts = supabase_admin.table("manuscripts")
    manuscripts.execute.side_effect = [
        _Resp(data={"id": "m1", "status": "pre_check"}),  # get_manuscript
    ]

    with pytest.raises(Exception):
        svc.update_status(manuscript_id="m1", to_status="published", changed_by="u1", allow_skip=False)


def test_update_status_allows_skip_when_admin(supabase_admin):
    svc = editorial_service_module.EditorialService()

    manuscripts = supabase_admin.table("manuscripts")
    manuscripts.execute.side_effect = [
        _Resp(data={"id": "m1", "status": "pre_check"}),  # get_manuscript
        _Resp(data=[{"id": "m1", "status": "published"}]),  # update
    ]

    # log 写入失败也不能阻断
    logs = supabase_admin.table("status_transition_logs")
    logs.execute.side_effect = RuntimeError("no table")

    out = svc.update_status(manuscript_id="m1", to_status="published", changed_by="u1", allow_skip=True)
    assert out["status"] == "published"


def test_update_invoice_info_updates_metadata_and_writes_audit_log(supabase_admin):
    svc = editorial_service_module.EditorialService()

    manuscripts = supabase_admin.table("manuscripts")
    manuscripts.execute.side_effect = [
        _Resp(data={"id": "m1", "status": "decision", "invoice_metadata": {"authors": "Old"}}),  # get_manuscript
        _Resp(data=[{"id": "m1", "status": "decision", "invoice_metadata": {"authors": "New"}}]),  # update
    ]

    logs = supabase_admin.table("status_transition_logs")
    logs.execute.return_value = _Resp(data=[{"id": "l1"}])

    out = svc.update_invoice_info(manuscript_id="m1", authors="New", changed_by="u1")
    assert out["id"] == "m1"
    assert logs.insert.called is True


def test_update_invoice_info_audit_payload_contains_before_after(supabase_admin):
    svc = editorial_service_module.EditorialService()

    manuscripts = supabase_admin.table("manuscripts")
    manuscripts.execute.side_effect = [
        _Resp(
            data={
                "id": "m1",
                "status": "decision",
                "invoice_metadata": {"authors": "A", "apc_amount": 100},
            }
        ),
        _Resp(data=[{"id": "m1", "status": "decision", "invoice_metadata": {"authors": "B", "apc_amount": 200}}]),
    ]

    logs = supabase_admin.table("status_transition_logs")
    logs.execute.return_value = _Resp(data=[{"id": "l1"}])

    svc.update_invoice_info(manuscript_id="m1", authors="B", apc_amount=200, changed_by="u1")
    inserted = logs.insert.call_args[0][0]
    payload = inserted.get("payload") or {}
    assert payload.get("action") == "update_invoice_info"
    assert (payload.get("before") or {}).get("authors") == "A"
    assert (payload.get("after") or {}).get("authors") == "B"
