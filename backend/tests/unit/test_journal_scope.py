from types import SimpleNamespace

import app.core.journal_scope as journal_scope


class _ScopeQuery:
    def __init__(self, data):
        self._data = data

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def in_(self, *_args, **_kwargs):
        return self

    def execute(self):
        return SimpleNamespace(data=self._data)


class _ScopeClient:
    def __init__(self, data):
        self._data = data

    def table(self, name: str):
        assert name == "journal_role_scopes"
        return _ScopeQuery(self._data)


def test_get_user_scope_journal_ids_supports_academic_editor(monkeypatch):
    monkeypatch.setattr(
        journal_scope,
        "supabase_admin",
        _ScopeClient([{"journal_id": "journal-a", "role": "academic_editor"}]),
    )

    allowed = journal_scope.get_user_scope_journal_ids(
        user_id="academic-user-1",
        roles=["academic_editor"],
    )

    assert allowed == {"journal-a"}
