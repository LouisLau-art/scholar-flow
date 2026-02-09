from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import BackgroundTasks, HTTPException

from app.api.v1 import editor as editor_api
from app.api.v1 import plagiarism as plagiarism_api
from app.api.v1 import stats as stats_api
from app.models.plagiarism import PlagiarismRetryRequest


@pytest.mark.asyncio
async def test_stats_endpoints(client, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}

    author_resp = await client.get("/api/v1/stats/author", headers=headers)
    editor_resp = await client.get("/api/v1/stats/editor", headers=headers)
    system_resp = await client.get("/api/v1/stats/system")

    assert author_resp.status_code == 200
    assert editor_resp.status_code == 200
    assert system_resp.status_code == 200


@pytest.mark.asyncio
async def test_record_download_invalid_id():
    with pytest.raises(HTTPException) as exc:
        await stats_api.record_download("")

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_record_download_exception(monkeypatch):
    class Boom:
        @staticmethod
        def now():
            raise RuntimeError("boom")

    monkeypatch.setattr(stats_api, "datetime", Boom)

    with pytest.raises(HTTPException) as exc:
        await stats_api.record_download("article-1")

    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_plagiarism_download_url(monkeypatch):
    report_id = UUID(int=1)
    class _FakeSvc:
        def get_report_by_id(self, _id: str):
            return {"id": _id, "report_url": f"https://reports.example/{_id}.pdf"}
        def get_download_url(self, report):
            return report["report_url"]
    monkeypatch.setattr(plagiarism_api, "PlagiarismService", _FakeSvc)

    result = await plagiarism_api.get_report_download_url(report_id)

    assert str(report_id) in result["download_url"]


@pytest.mark.asyncio
async def test_retry_plagiarism_check_adds_task(monkeypatch):
    import os
    os.environ["PLAGIARISM_CHECK_ENABLED"] = "1"
    class _FakeSvc:
        def get_report_by_manuscript(self, _mid: str):
            return None
        def ensure_report(self, manuscript_id: str, *, reset_status: bool = False):
            return {"manuscript_id": manuscript_id, "status": "pending", "reset": reset_status}
    monkeypatch.setattr(plagiarism_api, "PlagiarismService", _FakeSvc)
    request = PlagiarismRetryRequest(manuscript_id=UUID(int=2))
    tasks = BackgroundTasks()

    result = await plagiarism_api.retry_plagiarism_check(request, tasks)

    assert result["success"] is True
    assert len(tasks.tasks) == 1


class _FakeSupabase:
    def __init__(
        self,
        pipeline_data,
        reviewers_data,
        decision_data,
        raise_on_update=False,
        *,
        invoice_rows=None,
        manuscript_single=None,
    ):
        self.pipeline_data = pipeline_data
        self.reviewers_data = reviewers_data
        self.decision_data = decision_data
        self.raise_on_update = raise_on_update
        self.invoice_rows = invoice_rows or []
        self.manuscript_single = (
            manuscript_single
            if manuscript_single is not None
            else {"id": "1", "status": "decision"}
        )

    def table(self, name):
        return _FakeQuery(self, name)


class _FakeQuery:
    def __init__(self, parent, name):
        self.parent = parent
        self.name = name
        self._status = None
        self._update_payload = None
        self._single = False

    def select(self, *_args, **_kwargs):
        return self

    def update(self, payload):
        self._update_payload = payload
        return self

    def upsert(self, payload, *_args, **_kwargs):
        self._update_payload = payload
        return self

    def contains(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def eq(self, key, value):
        if key == "status":
            self._status = value
        return self

    def single(self, *_args, **_kwargs):
        self._single = True
        return self

    def execute(self):
        if self.name == "user_profiles":
            return (None, self.parent.reviewers_data)
        if self.name == "invoices":
            return SimpleNamespace(data=self.parent.invoice_rows)
        if self.name == "manuscripts" and self._single:
            return SimpleNamespace(data=self.parent.manuscript_single)
        if self.name == "manuscripts" and self._update_payload is not None:
            if self.parent.raise_on_update:
                raise RuntimeError("boom")
            return SimpleNamespace(data=self.parent.decision_data)
        if self.name == "manuscripts" and self._status:
            return (None, self.parent.pipeline_data.get(self._status, []))
        return (None, [])


@pytest.mark.asyncio
async def test_editor_pipeline_with_stubbed_supabase(monkeypatch):
    pipeline_data = {
        "pre_check": [{"id": "1"}],
        "under_review": [{"id": "2"}],
        "decision": [{"id": "3"}],
        "published": [{"id": "4"}],
    }
    fake = _FakeSupabase(pipeline_data, reviewers_data=[], decision_data=[])

    monkeypatch.setattr(editor_api, "supabase_admin", fake)

    result = await editor_api.get_editor_pipeline(current_user={"id": "user"})

    assert result["data"]["pending_quality"][0]["id"] == "1"
    assert result["data"]["published"][0]["id"] == "4"


@pytest.mark.asyncio
async def test_editor_available_reviewers_with_defaults(monkeypatch):
    reviewers = [
        {"id": "1", "email": "a@example.com", "roles": ["reviewer"]},
        {"id": "2", "email": "b@example.com", "roles": ["reviewer"]},
    ]
    fake = _FakeSupabase(pipeline_data={}, reviewers_data=reviewers, decision_data=[])

    monkeypatch.setattr(editor_api, "supabase", fake)

    result = await editor_api.get_available_reviewers(current_user={"id": "user"})

    assert result["data"][0]["affiliation"] == "Independent Researcher"
    assert result["data"][0]["review_count"] == 0


@pytest.mark.asyncio
async def test_editor_submit_decision_accept(monkeypatch):
    fake = _FakeSupabase(
        pipeline_data={}, reviewers_data=[], decision_data=[{"id": "1"}]
    )
    monkeypatch.setattr(editor_api, "supabase_admin", fake)

    result = await editor_api.submit_final_decision(
        current_user={"id": "user"},
        manuscript_id="1",
        decision="accept",
        comment="",
        apc_amount=1500,
    )

    assert result["data"]["status"] == "approved"


@pytest.mark.asyncio
async def test_editor_submit_decision_reject(monkeypatch):
    fake = _FakeSupabase(
        pipeline_data={}, reviewers_data=[], decision_data=[{"id": "1"}]
    )
    monkeypatch.setattr(editor_api, "supabase_admin", fake)

    result = await editor_api.submit_final_decision(
        current_user={"id": "user"},
        manuscript_id="1",
        decision="reject",
        comment="needs work",
    )

    assert result["data"]["status"] == "rejected"


@pytest.mark.asyncio
async def test_editor_submit_decision_invalid():
    with pytest.raises(HTTPException) as exc:
        await editor_api.submit_final_decision(
            current_user={"id": "user"},
            manuscript_id="1",
            decision="maybe",
            comment="",
        )

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_editor_submit_decision_not_found(monkeypatch):
    fake = _FakeSupabase(
        pipeline_data={},
        reviewers_data=[],
        decision_data=[],
        manuscript_single={},
    )
    monkeypatch.setattr(editor_api, "supabase_admin", fake)

    with pytest.raises(HTTPException) as exc:
        await editor_api.submit_final_decision(
            current_user={"id": "user"},
            manuscript_id="missing",
            decision="accept",
            comment="",
            apc_amount=1500,
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_editor_submit_decision_exception(monkeypatch):
    fake = _FakeSupabase(
        pipeline_data={},
        reviewers_data=[],
        decision_data=[],
        raise_on_update=True,
        manuscript_single={"id": "1", "status": "decision"},
    )
    monkeypatch.setattr(editor_api, "supabase_admin", fake)

    with pytest.raises(HTTPException) as exc:
        await editor_api.submit_final_decision(
            current_user={"id": "user"},
            manuscript_id="1",
            decision="accept",
            comment="",
            apc_amount=1500,
        )

    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_editor_submit_decision_requires_decision_stage(monkeypatch):
    fake = _FakeSupabase(
        pipeline_data={},
        reviewers_data=[],
        decision_data=[{"id": "1"}],
        manuscript_single={"id": "1", "status": "under_review"},
    )
    monkeypatch.setattr(editor_api, "supabase_admin", fake)

    with pytest.raises(HTTPException) as exc:
        await editor_api.submit_final_decision(
            current_user={"id": "user"},
            manuscript_id="1",
            decision="reject",
            comment="needs work",
        )

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_editor_test_endpoints():
    pipeline = await editor_api.get_editor_pipeline_test()
    reviewers = await editor_api.get_available_reviewers_test()
    decision = await editor_api.submit_final_decision_test(
        manuscript_id="1", decision="accept", comment=""
    )

    assert pipeline["success"] is True
    assert reviewers["success"] is True
    assert decision["data"]["status"] == "published"


def test_extract_supabase_error_none():
    response = SimpleNamespace(error=None)
    assert editor_api._extract_supabase_error(response) is None


def test_extract_supabase_error_tuple():
    response = ("boom", [])
    assert editor_api._extract_supabase_error(response) == "boom"


def test_is_missing_column_error():
    assert (
        editor_api._is_missing_column_error('column "published_at" does not exist')
        is True
    )
    assert editor_api._is_missing_column_error("some other error") is False


@pytest.mark.asyncio
async def test_editor_submit_decision_fallback_on_missing_column(monkeypatch):
    class _FallbackQuery:
        def __init__(self, parent, name: str):
            self.parent = parent
            self.name = name
            self._single = False

        def update(self, _payload):
            return self

        def upsert(self, _payload, *_args, **_kwargs):
            return self

        def select(self, *_args, **_kwargs):
            return self

        def single(self, *_args, **_kwargs):
            self._single = True
            return self

        def eq(self, *_args, **_kwargs):
            return self

        def limit(self, *_args, **_kwargs):
            return self

        def execute(self):
            if self._single:
                return SimpleNamespace(data={"id": "1", "status": "decision", "author_id": "user", "title": "t"})
            if self.name == "invoices":
                return SimpleNamespace(data=[{"id": "inv-1"}])
            self.parent.calls += 1
            if self.parent.calls == 1:
                raise RuntimeError('column "published_at" does not exist')
            return SimpleNamespace(data=[{"id": "1"}])

    class _FallbackSupabase:
        def __init__(self):
            self.calls = 0

        def table(self, name):
            return _FallbackQuery(self, name)

    monkeypatch.setattr(editor_api, "supabase_admin", _FallbackSupabase())

    result = await editor_api.submit_final_decision(
        current_user={"id": "user"},
        manuscript_id="1",
        decision="accept",
        comment="",
        apc_amount=1500,
    )

    assert result["data"]["status"] == "approved"


@pytest.mark.asyncio
async def test_editor_publish_fallback_on_missing_column(monkeypatch):
    class _FallbackQuery:
        def __init__(self, parent, name: str):
            self.parent = parent
            self.name = name
            self._single = False

        def select(self, *_args, **_kwargs):
            return self

        def single(self, *_args, **_kwargs):
            self._single = True
            return self

        def limit(self, *_args, **_kwargs):
            return self

        def update(self, _payload):
            return self

        def eq(self, *_args, **_kwargs):
            return self

        def execute(self):
            if self._single:
                return SimpleNamespace(data={"id": "1", "status": "approved"})
            if self.name == "invoices":
                return SimpleNamespace(data=[{"amount": 0, "status": "unpaid"}])
            self.parent.calls += 1
            if self.parent.calls == 1:
                raise RuntimeError('column "published_at" does not exist')
            return SimpleNamespace(data=[{"id": "1", "status": "published"}])

    class _FallbackSupabase:
        def __init__(self):
            self.calls = 0

        def table(self, name):
            return _FallbackQuery(self, name)

    from app.services import post_acceptance_service

    monkeypatch.setattr(post_acceptance_service, "supabase_admin", _FallbackSupabase())

    result = await editor_api.publish_manuscript_dev(
        current_user={"id": "user"},
        _profile={"roles": ["editor"]},
        manuscript_id="1",
    )

    assert result["data"]["status"] == "published"
