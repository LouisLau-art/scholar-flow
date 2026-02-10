from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.internal_collaboration_service import (
    InternalCollaborationService,
    MentionValidationError,
    _missing_table_from_error,
)


class _FakeNotifier:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def create_notification(self, **kwargs):
        self.calls.append(kwargs)
        return {"id": str(uuid4())}


class _FakeTable:
    def __init__(self, db: "_FakeDB", name: str) -> None:
        self.db = db
        self.name = name
        self._op = ""
        self._payload = None

    def insert(self, payload):
        self._op = "insert"
        self._payload = payload
        return self

    def execute(self):
        if self._op == "insert" and self.name == "internal_comments":
            row = dict(self._payload)
            row["id"] = self.db.comment_id
            self.db.comment_insert_payload = dict(self._payload)
            return SimpleNamespace(data=[row])
        if self._op == "insert" and self.name == "internal_comment_mentions":
            self.db.mention_insert_payload = list(self._payload)
            return SimpleNamespace(data=list(self._payload))
        return SimpleNamespace(data=[])


class _FakeDB:
    def __init__(self, comment_id: str) -> None:
        self.comment_id = comment_id
        self.comment_insert_payload: dict | None = None
        self.mention_insert_payload: list[dict] = []

    def table(self, name: str):
        return _FakeTable(self, name)


class _FakeFKTable(_FakeTable):
    def execute(self):
        if self._op == "insert" and self.name == "internal_comments":
            row = dict(self._payload)
            row["id"] = self.db.comment_id
            return SimpleNamespace(data=[row])
        if self._op == "insert" and self.name == "internal_comment_mentions":
            raise RuntimeError(
                'insert or update on table "internal_comment_mentions" violates foreign key constraint '
                '"internal_comment_mentions_mentioned_user_id_fkey"; '
                "Key (mentioned_user_id)=(00000000-0000-0000-0000-000000000001) is not present in table \"users\"."
            )
        return SimpleNamespace(data=[])


class _FakeFKDB(_FakeDB):
    def table(self, name: str):
        return _FakeFKTable(self, name)


def test_create_comment_dedups_mentions_and_notifies_once(monkeypatch: pytest.MonkeyPatch):
    author_id = str(uuid4())
    mentioned_id = str(uuid4())
    comment_id = str(uuid4())

    fake_db = _FakeDB(comment_id=comment_id)
    notifier = _FakeNotifier()
    svc = InternalCollaborationService(client=fake_db, notification_service=notifier)

    # 绕过 user_profiles 查询，聚焦“去重 + 通知一次”行为。
    monkeypatch.setattr(svc, "_validate_mention_targets", lambda ids: ids)
    monkeypatch.setattr(
        svc,
        "_load_profiles_map",
        lambda _ids: {author_id: {"id": author_id, "full_name": "Editor A", "email": "editor@example.com"}},
    )

    out = svc.create_comment(
        manuscript_id=str(uuid4()),
        author_user_id=author_id,
        content="Please check this update.",
        mention_user_ids=[mentioned_id, mentioned_id, author_id],
    )

    assert out["id"] == comment_id
    assert out["mention_user_ids"] == [mentioned_id]

    # 自己提及不会发通知，只会给真正被提及对象发一次。
    assert len(notifier.calls) == 1
    assert notifier.calls[0]["user_id"] == mentioned_id

    assert len(fake_db.mention_insert_payload) == 1
    assert fake_db.mention_insert_payload[0]["mentioned_user_id"] == mentioned_id


def test_create_comment_rejects_invalid_mention_id():
    svc = InternalCollaborationService(client=_FakeDB(comment_id=str(uuid4())), notification_service=_FakeNotifier())

    with pytest.raises(MentionValidationError) as ei:
        svc.create_comment(
            manuscript_id=str(uuid4()),
            author_user_id=str(uuid4()),
            content="hello",
            mention_user_ids=["not-a-uuid"],
        )

    assert ei.value.invalid_user_ids == ["not-a-uuid"]


def test_create_comment_maps_fk_violation_to_invalid_mentions(monkeypatch: pytest.MonkeyPatch):
    author_id = str(uuid4())
    mentioned_id = str(uuid4())
    svc = InternalCollaborationService(
        client=_FakeFKDB(comment_id=str(uuid4())),
        notification_service=_FakeNotifier(),
    )
    monkeypatch.setattr(svc, "_validate_mention_targets", lambda ids: ids)
    monkeypatch.setattr(
        svc,
        "_load_profiles_map",
        lambda _ids: {author_id: {"id": author_id, "full_name": "Editor A", "email": "editor@example.com"}},
    )

    with pytest.raises(MentionValidationError) as ei:
        svc.create_comment(
            manuscript_id=str(uuid4()),
            author_user_id=author_id,
            content="please check",
            mention_user_ids=[mentioned_id],
        )

    assert ei.value.invalid_user_ids == ["00000000-0000-0000-0000-000000000001"]


class _MissingCommentsTable:
    def table(self, name: str):
        return self

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def execute(self):
        raise RuntimeError(
            "Could not find the table 'public.internal_comments' in the schema cache (PGRST205)"
        )


def test_list_comments_returns_empty_when_internal_comments_missing_in_schema_cache():
    svc = InternalCollaborationService(client=_MissingCommentsTable(), notification_service=_FakeNotifier())
    rows = svc.list_comments(str(uuid4()))
    assert rows == []


def test_missing_table_parser_supports_pgrst205_schema_cache_message():
    error = RuntimeError("Could not find the table 'public.internal_comments' in the schema cache")
    assert _missing_table_from_error(error) == "internal_comments"


class _SilentError(Exception):
    def __str__(self) -> str:  # pragma: no cover - 专用于模拟第三方异常行为
        return ""


def test_missing_table_parser_reads_error_args_when_str_is_empty():
    error = _SilentError("Could not find the table 'public.internal_comments' in the schema cache")
    assert _missing_table_from_error(error) == "internal_comments"


class _DictArgsError(Exception):
    def __str__(self) -> str:  # pragma: no cover - 专用于模拟第三方异常行为
        return ""

    def __repr__(self) -> str:  # pragma: no cover - 专用于模拟第三方异常行为
        return "APIError()"


def test_missing_table_parser_supports_double_quote_table_message():
    error = _DictArgsError(
        {
            "message": 'Could not find the table "public.internal_comments" in the schema cache',
            "code": "PGRST205",
        }
    )
    assert _missing_table_from_error(error) == "internal_comments"
