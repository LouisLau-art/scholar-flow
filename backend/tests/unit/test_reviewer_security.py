from unittest.mock import MagicMock

import pytest

import app.services.reviewer_service as reviewer_service_module


class _Resp:
    def __init__(self, *, data=None):
        self.data = data


def _chain():
    q = MagicMock()
    for method in ("select", "eq", "single", "execute"):
        getattr(q, method).return_value = q
    return q


@pytest.fixture
def supabase_admin(monkeypatch: pytest.MonkeyPatch):
    client = MagicMock()
    tables: dict[str, MagicMock] = {}

    def _table(name: str):
        tables.setdefault(name, _chain())
        return tables[name]

    client.table.side_effect = _table
    client._tables = tables  # type: ignore[attr-defined]
    monkeypatch.setattr(reviewer_service_module, "supabase_admin", client)
    return client


def test_assignment_missing_should_fail(supabase_admin):
    svc = reviewer_service_module.ReviewerWorkspaceService()
    assignments = supabase_admin.table("review_assignments")
    assignments.execute.return_value = _Resp(data=None)

    with pytest.raises(ValueError):
        svc.get_workspace_data(
            assignment_id=reviewer_service_module.UUID("00000000-0000-0000-0000-000000000001"),
            reviewer_id=reviewer_service_module.UUID("00000000-0000-0000-0000-000000000002"),
        )


def test_assignment_owner_mismatch_should_fail(supabase_admin):
    svc = reviewer_service_module.ReviewerWorkspaceService()
    assignments = supabase_admin.table("review_assignments")
    assignments.execute.return_value = _Resp(
        data={
            "id": "a1",
            "manuscript_id": "m1",
            "reviewer_id": "00000000-0000-0000-0000-000000000099",
            "status": "pending",
        }
    )

    with pytest.raises(PermissionError):
        svc.get_workspace_data(
            assignment_id=reviewer_service_module.UUID("00000000-0000-0000-0000-000000000001"),
            reviewer_id=reviewer_service_module.UUID("00000000-0000-0000-0000-000000000002"),
        )
