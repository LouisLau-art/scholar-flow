import pytest
import asyncio
from httpx import AsyncClient
from unittest.mock import MagicMock, patch

# === 并发请求: 审稿分配 ===

class _FakeResp:
    def __init__(self, data=None, count=None):
        self.data = data
        self.count = count


class _FakeQuery:
    def __init__(self, table_name: str):
        self._table = table_name
        self._op = None
        self._payload = None
        self._filters = {}
        self._single = False

    # Chain builders
    def select(self, *_args, **_kwargs):
        self._op = "select"
        return self

    def insert(self, payload):
        self._op = "insert"
        self._payload = payload
        return self

    def update(self, payload):
        self._op = "update"
        self._payload = payload
        return self

    def delete(self):
        self._op = "delete"
        return self

    def eq(self, key, value):
        self._filters[key] = value
        return self

    def in_(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def single(self):
        self._single = True
        return self

    def execute(self):
        # manuscripts: 返回 author_id，避免触发“作者不能评审自己的稿件”
        if self._table == "manuscripts" and self._op == "select":
            return _FakeResp({"author_id": "author-1", "title": "t", "version": 1})

        # review_assignments: 幂等检查返回空；insert 返回一条记录
        if self._table == "review_assignments":
            if self._op == "select":
                return _FakeResp([])
            if self._op == "insert":
                rid = (self._payload or {}).get("reviewer_id", "r")
                return _FakeResp([{"id": f"assign-{rid}", "status": "pending"}])
            if self._op in {"update", "delete"}:
                return _FakeResp([])

        # user_profiles / review_reports / notifications：不关心具体返回
        if self._op == "select" and self._single:
            return _FakeResp({"email": "reviewer@example.com"})
        return _FakeResp([])


class _FakeSupabase:
    def table(self, name: str):
        return _FakeQuery(name)

@pytest.mark.asyncio
async def test_concurrent_reviewer_assignments(client: AsyncClient, auth_token: str, monkeypatch):
    """验证并发分配审稿人不会导致异常"""
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")
    fake = _FakeSupabase()

    with patch("app.api.v1.reviews.supabase", fake), \
         patch("app.api.v1.reviews.supabase_admin", fake), \
         patch("app.api.v1.reviews.NotificationService.create_notification", MagicMock(return_value=None)):
        async def assign(i: int):
            return await client.post(
                "/api/v1/reviews/assign",
                json={
                    "manuscript_id": "00000000-0000-0000-0000-000000000000",
                    "reviewer_id": f"00000000-0000-0000-0000-00000000000{i}",
                },
                headers={"Authorization": f"Bearer {auth_token}"},
            )

        results = await asyncio.gather(*[assign(i) for i in range(5)])

        assert all(r.status_code == 200 for r in results)
        assert all(r.json().get("success") is True for r in results)
