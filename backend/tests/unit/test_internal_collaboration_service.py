from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.internal_collaboration_service import InternalCollaborationService, MentionValidationError


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
