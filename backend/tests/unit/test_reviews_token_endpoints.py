import io
from types import SimpleNamespace
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from starlette.datastructures import UploadFile

from app.api.v1 import reviews as reviews_api


class _FakeStorageBucket:
    def __init__(self):
        self.upload_calls = []

    def upload(self, path, content, options=None):
        self.upload_calls.append((path, content, options))
        return {"ok": True}


class _FakeStorage:
    def __init__(self):
        self.bucket = _FakeStorageBucket()

    def from_(self, *_args, **_kwargs):
        return self.bucket


class _FakeSupabaseAdmin:
    def __init__(self, *, review_by_token=None, manuscript=None, review_rows=None):
        self._review_by_token = review_by_token or {}
        self._manuscript = manuscript or {"id": "m-1", "title": "T", "abstract": "A", "file_path": None, "status": "under_review"}
        self._review_rows = review_rows or []
        self.storage = _FakeStorage()
        self.last_update = None

    def table(self, name: str):
        return _FakeQuery(self, name)


class _FakeQuery:
    def __init__(self, parent: _FakeSupabaseAdmin, name: str):
        self.parent = parent
        self.name = name
        self._single = False
        self._filters = {}
        self._update_payload = None

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, key, value):
        self._filters[key] = value
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def single(self, *_args, **_kwargs):
        self._single = True
        return self

    def update(self, payload):
        self._update_payload = payload
        return self

    def execute(self):
        if self.name == "review_reports" and self._filters.get("token"):
            token = self._filters["token"]
            return SimpleNamespace(data=self.parent._review_by_token.get(token, {}))
        if self.name == "review_reports" and self._update_payload is not None:
            self.parent.last_update = self._update_payload
            return SimpleNamespace(data=[{"id": "rr-1"}])
        if self.name == "review_reports":
            return SimpleNamespace(data=self.parent._review_rows)
        if self.name == "manuscripts":
            return SimpleNamespace(data=self.parent._manuscript)
        return SimpleNamespace(data=[])


@pytest.mark.asyncio
async def test_get_review_by_token_success(monkeypatch):
    token = "tok_1"
    fake = _FakeSupabaseAdmin(
        review_by_token={
            token: {
                "id": "rr-1",
                "manuscript_id": "m-1",
                "reviewer_id": "r-1",
                "status": "invited",
                "expiry_date": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            }
        }
    )
    monkeypatch.setattr(reviews_api, "supabase_admin", fake)

    result = await reviews_api.get_review_by_token(token)
    assert result["success"] is True
    assert result["data"]["review_report"]["id"] == "rr-1"
    assert result["data"]["manuscript"]["id"] == "m-1"


@pytest.mark.asyncio
async def test_get_review_by_token_expired(monkeypatch):
    token = "tok_expired"
    fake = _FakeSupabaseAdmin(
        review_by_token={
            token: {
                "id": "rr-1",
                "manuscript_id": "m-1",
                "reviewer_id": "r-1",
                "status": "invited",
                "expiry_date": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
            }
        }
    )
    monkeypatch.setattr(reviews_api, "supabase_admin", fake)

    with pytest.raises(HTTPException) as exc:
        await reviews_api.get_review_by_token(token)
    assert exc.value.status_code == 410


@pytest.mark.asyncio
async def test_submit_review_by_token_uploads_attachment(monkeypatch):
    token = "tok_submit"
    fake = _FakeSupabaseAdmin(
        review_by_token={
            token: {
                "id": "rr-1",
                "manuscript_id": "m-1",
                "reviewer_id": "r-1",
                "status": "invited",
                "expiry_date": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            }
        }
    )
    monkeypatch.setattr(reviews_api, "supabase_admin", fake)

    upload = UploadFile(filename="annotated.pdf", file=io.BytesIO(b"%PDF-1.4 mocked"))
    result = await reviews_api.submit_review_by_token(
        token=token,
        content="Public comments",
        score=5,
        confidential_comments_to_editor="Confidential",
        attachment=upload,
    )

    assert result["success"] is True
    assert fake.storage.bucket.upload_calls, "expected storage upload to be called"
    assert fake.last_update is not None
    assert fake.last_update["confidential_comments_to_editor"] == "Confidential"
    assert fake.last_update["attachment_path"] is not None


@pytest.mark.asyncio
async def test_get_review_feedback_sanitizes_for_author(monkeypatch):
    fake = _FakeSupabaseAdmin(
        manuscript={"id": "m-1", "author_id": "a-1"},
        review_rows=[
            {
                "id": "rr-1",
                "manuscript_id": "m-1",
                "reviewer_id": "r-1",
                "status": "completed",
                "content": "Public",
                "score": 4,
                "confidential_comments_to_editor": "secret",
                "attachment_path": "secret.pdf",
            }
        ],
    )
    monkeypatch.setattr(reviews_api, "supabase_admin", fake)

    result = await reviews_api.get_review_feedback_for_manuscript(
        manuscript_id="m-1",  # FastAPI 会传 UUID，这里直接走字符串也可覆盖逻辑
        current_user={"id": "a-1", "email": "author@example.com"},
    )
    assert result["success"] is True
    item = result["data"][0]
    assert item["content"] == "Public"
    assert "confidential_comments_to_editor" not in item
    assert "attachment_path" not in item


@pytest.mark.asyncio
async def test_submit_review_by_token_rejects_invalid_score():
    with pytest.raises(HTTPException) as exc:
        await reviews_api.submit_review_by_token(
            token="tok",
            content="ok",
            score=9,
            confidential_comments_to_editor=None,
            attachment=None,
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_get_review_feedback_forbidden_when_not_author_or_admin(monkeypatch):
    fake = _FakeSupabaseAdmin(
        manuscript={"id": "m-1", "author_id": "author-1"},
        review_rows=[],
    )
    monkeypatch.setattr(reviews_api, "supabase_admin", fake)

    with pytest.raises(HTTPException) as exc:
        await reviews_api.get_review_feedback_for_manuscript(
            manuscript_id="m-1",
            current_user={"id": "someone-else", "email": "nope@example.com"},
        )
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_get_review_feedback_includes_confidential_for_admin(monkeypatch):
    fake = _FakeSupabaseAdmin(
        manuscript={"id": "m-1", "author_id": "author-1"},
        review_rows=[
            {
                "id": "rr-1",
                "manuscript_id": "m-1",
                "reviewer_id": "r-1",
                "status": "completed",
                "content": "Public",
                "score": 4,
                "confidential_comments_to_editor": "secret",
                "attachment_path": "secret.pdf",
            }
        ],
    )
    monkeypatch.setattr(reviews_api, "supabase_admin", fake)
    monkeypatch.setenv("ADMIN_EMAILS", "admin@example.com")

    result = await reviews_api.get_review_feedback_for_manuscript(
        manuscript_id="m-1",
        current_user={"id": "not-author", "email": "admin@example.com"},
    )
    assert result["success"] is True
    item = result["data"][0]
    assert item.get("confidential_comments_to_editor") == "secret"
    assert item.get("attachment_path") == "secret.pdf"
