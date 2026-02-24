from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import pytest
from httpx import AsyncClient
from postgrest.exceptions import APIError

from app.core.roles import get_current_profile
from main import app
from .test_utils import insert_manuscript, make_user


class _MockResponse:
    def __init__(self, data: Any):
        self.data = data
        self.error = None


class _FakeTableQuery:
    def __init__(self, store: dict[str, list[dict[str, Any]]], table_name: str):
        self._store = store
        self._table_name = table_name
        self._eq_filters: list[tuple[str, Any]] = []
        self._in_filters: list[tuple[str, set[str]]] = []
        self._neq_filters: list[tuple[str, Any]] = []
        self._ilike_filters: list[tuple[str, str]] = []
        self._single = False
        self._limit: int | None = None
        self._order_key: str | None = None
        self._order_desc = False
        self._range: tuple[int, int] | None = None

    def select(self, *_args, **_kwargs):
        return self

    def order(self, key: str, desc: bool = False):
        self._order_key = key
        self._order_desc = bool(desc)
        return self

    def eq(self, key: str, value: Any):
        self._eq_filters.append((key, value))
        return self

    def in_(self, key: str, values: list[Any] | set[Any] | tuple[Any, ...]):
        normalized = {str(v) for v in values}
        self._in_filters.append((key, normalized))
        return self

    def neq(self, key: str, value: Any):
        self._neq_filters.append((key, value))
        return self

    def ilike(self, key: str, pattern: str):
        # 仅支持 %keyword% 形式，满足本文件测试即可
        needle = str(pattern or "").replace("%", "").strip().lower()
        self._ilike_filters.append((key, needle))
        return self

    def limit(self, value: int):
        self._limit = int(value)
        return self

    def range(self, start: int, end: int):
        self._range = (int(start), int(end))
        return self

    def single(self):
        self._single = True
        return self

    def execute(self):
        rows = [dict(item) for item in self._store.get(self._table_name, [])]

        for key, value in self._eq_filters:
            rows = [r for r in rows if r.get(key) == value]
        for key, values in self._in_filters:
            rows = [r for r in rows if str(r.get(key)) in values]
        for key, value in self._neq_filters:
            rows = [r for r in rows if r.get(key) != value]
        for key, needle in self._ilike_filters:
            if not needle:
                continue
            rows = [r for r in rows if needle in str(r.get(key) or "").lower()]

        if self._order_key:
            rows.sort(key=lambda r: str(r.get(self._order_key) or ""), reverse=self._order_desc)
        if self._range:
            start, end = self._range
            rows = rows[start : end + 1]
        if self._limit is not None:
            rows = rows[: self._limit]

        if self._single:
            return _MockResponse(rows[0] if rows else None)
        return _MockResponse(rows)


class _FakeSupabase:
    def __init__(self, store: dict[str, list[dict[str, Any]]]):
        self._store = store

    def table(self, table_name: str):
        return _FakeTableQuery(self._store, table_name)


@pytest.fixture
def override_profile_role():
    def _set(roles: list[str], *, user_id: str = "00000000-0000-0000-0000-000000000000"):
        app.dependency_overrides[get_current_profile] = lambda: {
            "id": user_id,
            "email": "rbac_scope_tester@example.com",
            "roles": roles,
        }

    yield _set
    app.dependency_overrides.pop(get_current_profile, None)


def _require_decision_audit_schema(db) -> None:
    checks = [
        ("manuscripts", "id,status,editor_id,invoice_metadata"),
        ("review_reports", "id,manuscript_id,status"),
        ("decision_letters", "id,manuscript_id,status,updated_at"),
        ("status_transition_logs", "id,manuscript_id,payload,created_at"),
    ]
    for table, cols in checks:
        try:
            db.table(table).select(cols).limit(1).execute()
        except APIError as e:
            pytest.skip(
                f"数据库缺少 RBAC 决策审计测试所需 schema（{table}/{cols}）：{getattr(e, 'message', str(e))}"
            )


def _cleanup_decision_records(db, manuscript_id: str, user_ids: list[str]) -> None:
    for table, column in (
        ("notifications", "manuscript_id"),
        ("status_transition_logs", "manuscript_id"),
        ("decision_letters", "manuscript_id"),
        ("review_reports", "manuscript_id"),
        ("invoices", "manuscript_id"),
        ("manuscripts", "id"),
    ):
        try:
            db.table(table).delete().eq(column, manuscript_id).execute()
        except Exception:
            pass
    for user_id in user_ids:
        try:
            db.table("user_profiles").delete().eq("id", user_id).execute()
        except Exception:
            pass


def _ensure_role_scope_binding(
    db,
    *,
    user_id: str,
    role: str,
    journal_id: str,
) -> None:
    try:
        db.table("journals").upsert(
            {
                "id": journal_id,
                "title": f"RBAC Journal {journal_id[:6]}",
                "slug": f"rbac-{journal_id[:8]}",
                "is_active": True,
            }
        ).execute()
    except Exception:
        db.table("journals").upsert(
            {
                "id": journal_id,
                "title": f"RBAC Journal {journal_id[:6]}",
                "slug": f"rbac-{journal_id[:8]}",
            }
        ).execute()

    db.table("journal_role_scopes").upsert(
        {
            "user_id": user_id,
            "journal_id": journal_id,
            "role": role,
            "is_active": True,
            "created_by": user_id,
        },
        on_conflict="user_id,journal_id,role",
    ).execute()


@pytest.mark.asyncio
async def test_process_role_matrix_allows_assistant_editor(
    client: AsyncClient,
    auth_token: str,
    override_profile_role,
    monkeypatch: pytest.MonkeyPatch,
):
    override_profile_role(["assistant_editor"])
    monkeypatch.setattr(
        "app.api.v1.editor.EditorService.list_manuscripts_process",
        lambda self, **kwargs: [],
    )
    response = await client.get(
        "/api/v1/editor/manuscripts/process",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body.get("success") is True


@pytest.mark.asyncio
async def test_rbac_context_returns_actions_and_scope(
    client: AsyncClient,
    auth_token: str,
    override_profile_role,
    monkeypatch: pytest.MonkeyPatch,
):
    user_id = "00000000-0000-0000-0000-000000000000"
    override_profile_role(["managing_editor"], user_id=user_id)
    monkeypatch.setenv("JOURNAL_SCOPE_ENFORCEMENT", "1")

    fake = _FakeSupabase(
        {
            "journal_role_scopes": [
                {
                    "id": str(uuid4()),
                    "user_id": user_id,
                    "journal_id": "j-allowed",
                    "role": "managing_editor",
                    "is_active": True,
                }
            ]
        }
    )
    monkeypatch.setattr("app.core.journal_scope.supabase_admin", fake)

    response = await client.get(
        "/api/v1/editor/rbac/context",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body.get("success") is True
    data = body.get("data") or {}
    assert "process:view" in (data.get("allowed_actions") or [])
    assert data.get("journal_scope", {}).get("allowed_journal_ids") == ["j-allowed"]


@pytest.mark.asyncio
async def test_process_list_trimmed_by_journal_scope(
    client: AsyncClient,
    auth_token: str,
    override_profile_role,
    monkeypatch: pytest.MonkeyPatch,
):
    user_id = "00000000-0000-0000-0000-000000000000"
    override_profile_role(["managing_editor"], user_id=user_id)
    monkeypatch.setenv("JOURNAL_SCOPE_ENFORCEMENT", "1")

    fake = _FakeSupabase(
        {
            "manuscripts": [
                {
                    "id": "m-allowed",
                    "title": "Allowed Manuscript",
                    "status": "under_review",
                    "created_at": "2026-02-10T00:00:00Z",
                    "updated_at": "2026-02-10T00:00:00Z",
                    "journal_id": "j-allowed",
                    "owner_id": None,
                    "editor_id": None,
                    "pre_check_status": None,
                    "assistant_editor_id": None,
                    "journals": {"title": "Allowed Journal", "slug": "allowed"},
                },
                {
                    "id": "m-forbidden",
                    "title": "Forbidden Manuscript",
                    "status": "under_review",
                    "created_at": "2026-02-10T00:00:00Z",
                    "updated_at": "2026-02-10T00:00:00Z",
                    "journal_id": "j-forbidden",
                    "owner_id": None,
                    "editor_id": None,
                    "pre_check_status": None,
                    "assistant_editor_id": None,
                    "journals": {"title": "Forbidden Journal", "slug": "forbidden"},
                },
            ],
            "journal_role_scopes": [
                {
                    "id": str(uuid4()),
                    "user_id": user_id,
                    "journal_id": "j-allowed",
                    "role": "managing_editor",
                    "is_active": True,
                }
            ],
            "user_profiles": [],
            "status_transition_logs": [],
            "internal_tasks": [],
        }
    )

    monkeypatch.setattr("app.services.editor_service.supabase_admin", fake)
    monkeypatch.setattr("app.core.journal_scope.supabase_admin", fake)

    response = await client.get(
        "/api/v1/editor/manuscripts/process",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload.get("success") is True
    rows = payload.get("data") or []
    assert [str(r.get("id")) for r in rows] == ["m-allowed"]


@pytest.mark.asyncio
async def test_process_list_me_without_scope_hidden_when_enforcement_off(
    client: AsyncClient,
    auth_token: str,
    override_profile_role,
    monkeypatch: pytest.MonkeyPatch,
):
    user_id = "00000000-0000-0000-0000-000000000000"
    override_profile_role(["managing_editor"], user_id=user_id)
    monkeypatch.setenv("JOURNAL_SCOPE_ENFORCEMENT", "0")

    fake = _FakeSupabase(
        {
            "manuscripts": [
                {
                    "id": "m-any",
                    "title": "Any Manuscript",
                    "status": "under_review",
                    "created_at": "2026-02-10T00:00:00Z",
                    "updated_at": "2026-02-10T00:00:00Z",
                    "journal_id": "j-any",
                    "owner_id": None,
                    "editor_id": None,
                    "pre_check_status": None,
                    "assistant_editor_id": None,
                    "journals": {"title": "Any Journal", "slug": "any"},
                }
            ],
            "journal_role_scopes": [],
            "user_profiles": [],
            "status_transition_logs": [],
            "internal_tasks": [],
        }
    )

    monkeypatch.setattr("app.services.editor_service.supabase_admin", fake)
    monkeypatch.setattr("app.core.journal_scope.supabase_admin", fake)

    response = await client.get(
        "/api/v1/editor/manuscripts/process",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload.get("success") is True
    assert payload.get("data") == []


@pytest.mark.asyncio
async def test_detail_cross_journal_forbidden(
    client: AsyncClient,
    auth_token: str,
    override_profile_role,
    monkeypatch: pytest.MonkeyPatch,
):
    user_id = "00000000-0000-0000-0000-000000000000"
    override_profile_role(["managing_editor"], user_id=user_id)
    monkeypatch.setenv("JOURNAL_SCOPE_ENFORCEMENT", "1")

    fake = _FakeSupabase(
        {
            "manuscripts": [
                {"id": "m-403", "journal_id": "j-forbidden"},
            ],
            "journal_role_scopes": [
                {
                    "id": str(uuid4()),
                    "user_id": user_id,
                    "journal_id": "j-allowed",
                    "role": "managing_editor",
                    "is_active": True,
                }
            ],
        }
    )
    monkeypatch.setattr("app.core.journal_scope.supabase_admin", fake)
    monkeypatch.setattr("app.api.v1.editor_detail.supabase_admin", fake)

    response = await client.get(
        "/api/v1/editor/manuscripts/m-403",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 403
    assert "journal scope" in str(response.json().get("detail", "")).lower()


@pytest.mark.asyncio
async def test_detail_me_without_scope_forbidden_when_enforcement_off(
    client: AsyncClient,
    auth_token: str,
    override_profile_role,
    monkeypatch: pytest.MonkeyPatch,
):
    user_id = "00000000-0000-0000-0000-000000000000"
    override_profile_role(["managing_editor"], user_id=user_id)
    monkeypatch.setenv("JOURNAL_SCOPE_ENFORCEMENT", "0")

    fake = _FakeSupabase(
        {
            "manuscripts": [
                {"id": "m-403", "journal_id": "j-forbidden"},
            ],
            "journal_role_scopes": [],
        }
    )
    monkeypatch.setattr("app.core.journal_scope.supabase_admin", fake)
    monkeypatch.setattr("app.api.v1.editor_detail.supabase_admin", fake)

    response = await client.get(
        "/api/v1/editor/manuscripts/m-403",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 403
    assert "journal scope" in str(response.json().get("detail", "")).lower()


@pytest.mark.asyncio
async def test_academic_queue_eic_without_scope_hidden_when_enforcement_off(
    client: AsyncClient,
    auth_token: str,
    override_profile_role,
    monkeypatch: pytest.MonkeyPatch,
):
    user_id = "11111111-1111-1111-1111-111111111111"
    override_profile_role(["editor_in_chief"], user_id=user_id)
    monkeypatch.setenv("JOURNAL_SCOPE_ENFORCEMENT", "0")

    fake = _FakeSupabase(
        {
            "manuscripts": [
                {
                    "id": "m-academic",
                    "title": "Academic Queue Manuscript",
                    "status": "pre_check",
                    "pre_check_status": "academic",
                    "journal_id": "j-any",
                    "owner_id": None,
                    "editor_id": None,
                    "assistant_editor_id": None,
                    "created_at": "2026-02-10T00:00:00Z",
                    "updated_at": "2026-02-10T00:00:00Z",
                }
            ],
            "journal_role_scopes": [],
            "user_profiles": [],
        }
    )

    monkeypatch.setattr("app.services.editor_service.supabase_admin", fake)
    monkeypatch.setattr("app.core.journal_scope.supabase_admin", fake)

    response = await client.get(
        "/api/v1/editor/academic",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 200, response.text
    assert response.json() == []


@pytest.mark.asyncio
async def test_cross_journal_write_forbidden_for_owner_and_invoice(
    client: AsyncClient,
    auth_token: str,
    override_profile_role,
    monkeypatch: pytest.MonkeyPatch,
):
    user_id = "00000000-0000-0000-0000-000000000000"
    override_profile_role(["managing_editor"], user_id=user_id)
    monkeypatch.setenv("JOURNAL_SCOPE_ENFORCEMENT", "1")

    fake = _FakeSupabase(
        {
            "manuscripts": [
                {"id": "m-403", "journal_id": "j-forbidden"},
            ],
            "journal_role_scopes": [
                {
                    "id": str(uuid4()),
                    "user_id": user_id,
                    "journal_id": "j-allowed",
                    "role": "managing_editor",
                    "is_active": True,
                }
            ],
        }
    )
    monkeypatch.setattr("app.core.journal_scope.supabase_admin", fake)

    bind_response = await client.post(
        "/api/v1/editor/manuscripts/m-403/bind-owner",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"owner_id": str(uuid4())},
    )
    assert bind_response.status_code == 403

    invoice_response = await client.put(
        "/api/v1/editor/manuscripts/m-403/invoice-info",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"authors": "A. Author"},
    )
    assert invoice_response.status_code == 403


@pytest.mark.asyncio
async def test_invoice_confirm_requires_confirm_paid_permission(
    client: AsyncClient,
    auth_token: str,
    override_profile_role,
):
    # 中文注释：
    # - assistant_editor 不具备财务确认权限；
    # - 应在动作级权限检查阶段直接被拒绝（不依赖 journal scope）。
    override_profile_role(["assistant_editor"])
    response = await client.post(
        "/api/v1/editor/invoices/confirm",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"manuscript_id": str(uuid4())},
    )
    assert response.status_code == 403
    assert "invoice:confirm_paid" in str(response.json().get("detail", ""))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_first_decision_semantics_keeps_status_and_writes_audit_event(
    client: AsyncClient,
    supabase_admin_client,
    set_admin_emails,
):
    set_admin_emails([])
    _require_decision_audit_schema(supabase_admin_client)

    managing_editor = make_user(email="rbac_first_decision_me@example.com")
    author = make_user(email="rbac_first_decision_author@example.com")
    reviewer = make_user(email="rbac_first_decision_reviewer@example.com")
    manuscript_id = str(uuid4())
    journal_id = str(uuid4())

    try:
        supabase_admin_client.table("user_profiles").upsert(
            {
                "id": managing_editor.id,
                "email": managing_editor.email,
                "roles": ["managing_editor"],
            }
        ).execute()
        _ensure_role_scope_binding(
            supabase_admin_client,
            user_id=managing_editor.id,
            role="managing_editor",
            journal_id=journal_id,
        )
        insert_manuscript(
            supabase_admin_client,
            manuscript_id=manuscript_id,
            author_id=author.id,
            status="decision",
            title="RBAC First Decision Manuscript",
            file_path=f"manuscripts/{manuscript_id}/v1.pdf",
            journal_id=journal_id,
        )
        supabase_admin_client.table("manuscripts").update({"editor_id": managing_editor.id}).eq(
            "id", manuscript_id
        ).execute()
        supabase_admin_client.table("review_reports").insert(
            {
                "manuscript_id": manuscript_id,
                "reviewer_id": reviewer.id,
                "status": "completed",
                "content": "Looks good with minor edits.",
                "score": 4,
            }
        ).execute()

        res = await client.post(
            f"/api/v1/editor/manuscripts/{manuscript_id}/submit-decision",
            headers={"Authorization": f"Bearer {managing_editor.token}"},
            json={
                "content": "First decision suggestion draft",
                "decision": "minor_revision",
                "is_final": False,
                "decision_stage": "first",
                "attachment_paths": [],
                "last_updated_at": None,
            },
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body.get("success") is True
        assert body["data"]["status"] == "draft"
        assert body["data"]["manuscript_status"] == "decision"

        ms = (
            supabase_admin_client.table("manuscripts")
            .select("status")
            .eq("id", manuscript_id)
            .single()
            .execute()
            .data
        )
        assert str(ms.get("status") or "") == "decision"

        logs = (
            supabase_admin_client.table("status_transition_logs")
            .select("payload,created_at")
            .eq("manuscript_id", manuscript_id)
            .order("created_at", desc=True)
            .execute()
        )
        rows = getattr(logs, "data", None) or []
        assert any(
            isinstance((r or {}).get("payload"), dict)
            and (r["payload"] or {}).get("action") == "first_decision_workspace"
            and (r["payload"] or {}).get("decision_stage") == "first"
            for r in rows
        )
    finally:
        try:
            supabase_admin_client.table("journal_role_scopes").delete().eq("journal_id", journal_id).execute()
        except Exception:
            pass
        try:
            supabase_admin_client.table("journals").delete().eq("id", journal_id).execute()
        except Exception:
            pass
        _cleanup_decision_records(
            supabase_admin_client,
            manuscript_id,
            [managing_editor.id, author.id, reviewer.id],
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_final_decision_requires_eic_or_admin(
    client: AsyncClient,
    supabase_admin_client,
    set_admin_emails,
):
    set_admin_emails([])
    _require_decision_audit_schema(supabase_admin_client)

    managing_editor = make_user(email="rbac_final_me@example.com")
    eic = make_user(email="rbac_final_eic@example.com")
    author = make_user(email="rbac_final_author@example.com")
    reviewer = make_user(email="rbac_final_reviewer@example.com")
    manuscript_id = str(uuid4())
    journal_id = str(uuid4())

    try:
        supabase_admin_client.table("user_profiles").upsert(
            {"id": managing_editor.id, "email": managing_editor.email, "roles": ["managing_editor"]}
        ).execute()
        supabase_admin_client.table("user_profiles").upsert(
            {"id": eic.id, "email": eic.email, "roles": ["editor_in_chief"]}
        ).execute()
        _ensure_role_scope_binding(
            supabase_admin_client,
            user_id=managing_editor.id,
            role="managing_editor",
            journal_id=journal_id,
        )
        _ensure_role_scope_binding(
            supabase_admin_client,
            user_id=eic.id,
            role="editor_in_chief",
            journal_id=journal_id,
        )
        insert_manuscript(
            supabase_admin_client,
            manuscript_id=manuscript_id,
            author_id=author.id,
            status="decision",
            title="RBAC Final Decision Manuscript",
            file_path=f"manuscripts/{manuscript_id}/v1.pdf",
            journal_id=journal_id,
        )
        supabase_admin_client.table("manuscripts").update({"editor_id": managing_editor.id}).eq(
            "id", manuscript_id
        ).execute()
        supabase_admin_client.table("review_reports").insert(
            {
                "manuscript_id": manuscript_id,
                "reviewer_id": reviewer.id,
                "status": "completed",
                "content": "Accept recommended.",
                "score": 5,
            }
        ).execute()
        supabase_admin_client.table("revisions").insert(
            {
                "manuscript_id": manuscript_id,
                "round_number": 1,
                "decision_type": "major",
                "editor_comment": "Please revise and resubmit.",
                "status": "submitted",
                "response_letter": "Author addressed all comments.",
                "submitted_at": datetime.now(timezone.utc).isoformat(),
            }
        ).execute()

        me_res = await client.post(
            f"/api/v1/editor/manuscripts/{manuscript_id}/submit-decision",
            headers={"Authorization": f"Bearer {managing_editor.token}"},
            json={
                "content": "ME final decision should be forbidden",
                "decision": "accept",
                "is_final": True,
                "decision_stage": "final",
                "attachment_paths": [],
                "last_updated_at": None,
            },
        )
        assert me_res.status_code == 403, me_res.text

        eic_res = await client.post(
            f"/api/v1/editor/manuscripts/{manuscript_id}/submit-decision",
            headers={"Authorization": f"Bearer {eic.token}"},
            json={
                "content": "EIC final decision",
                "decision": "accept",
                "is_final": True,
                "decision_stage": "final",
                "attachment_paths": [],
                "last_updated_at": None,
            },
        )
        assert eic_res.status_code == 200, eic_res.text
        assert eic_res.json()["data"]["manuscript_status"] == "approved"

        ms = (
            supabase_admin_client.table("manuscripts")
            .select("status")
            .eq("id", manuscript_id)
            .single()
            .execute()
            .data
        )
        assert str(ms.get("status") or "") == "approved"
    finally:
        try:
            supabase_admin_client.table("journal_role_scopes").delete().eq("journal_id", journal_id).execute()
        except Exception:
            pass
        try:
            supabase_admin_client.table("journals").delete().eq("id", journal_id).execute()
        except Exception:
            pass
        _cleanup_decision_records(
            supabase_admin_client,
            manuscript_id,
            [managing_editor.id, eic.id, author.id, reviewer.id],
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_apc_override_audit_payload_contains_before_after_reason_source(
    client: AsyncClient,
    supabase_admin_client,
    set_admin_emails,
):
    set_admin_emails([])
    _require_decision_audit_schema(supabase_admin_client)

    eic = make_user(email="rbac_apc_eic@example.com")
    author = make_user(email="rbac_apc_author@example.com")
    manuscript_id = str(uuid4())
    journal_id = str(uuid4())

    try:
        supabase_admin_client.table("user_profiles").upsert(
            {"id": eic.id, "email": eic.email, "roles": ["editor_in_chief"]}
        ).execute()
        _ensure_role_scope_binding(
            supabase_admin_client,
            user_id=eic.id,
            role="editor_in_chief",
            journal_id=journal_id,
        )
        insert_manuscript(
            supabase_admin_client,
            manuscript_id=manuscript_id,
            author_id=author.id,
            status="decision",
            title="RBAC APC Audit Manuscript",
            file_path=f"manuscripts/{manuscript_id}/v1.pdf",
            journal_id=journal_id,
        )
        supabase_admin_client.table("manuscripts").update(
            {
                "editor_id": eic.id,
                "invoice_metadata": {"authors": "Old Author", "apc_amount": 1200},
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", manuscript_id).execute()

        res = await client.put(
            f"/api/v1/editor/manuscripts/{manuscript_id}/invoice-info",
            headers={"Authorization": f"Bearer {eic.token}"},
            json={
                "authors": "Updated Author",
                "apc_amount": 1800,
                "reason": "manual override after committee approval",
                "source": "editor_manuscript_detail",
            },
        )
        assert res.status_code == 200, res.text
        assert res.json().get("success") is True

        logs = (
            supabase_admin_client.table("status_transition_logs")
            .select("payload,created_at")
            .eq("manuscript_id", manuscript_id)
            .order("created_at", desc=True)
            .execute()
        )
        rows = getattr(logs, "data", None) or []
        hit = next(
            (
                r
                for r in rows
                if isinstance((r or {}).get("payload"), dict)
                and (r["payload"] or {}).get("action") == "update_invoice_info"
            ),
            None,
        )
        assert hit is not None
        payload = hit.get("payload") or {}
        assert payload.get("source") == "editor_manuscript_detail"
        assert payload.get("reason") == "manual override after committee approval"
        assert int(float((payload.get("before") or {}).get("apc_amount") or 0)) == 1200
        assert int(float((payload.get("after") or {}).get("apc_amount") or 0)) == 1800
    finally:
        try:
            supabase_admin_client.table("journal_role_scopes").delete().eq("journal_id", journal_id).execute()
        except Exception:
            pass
        try:
            supabase_admin_client.table("journals").delete().eq("id", journal_id).execute()
        except Exception:
            pass
        _cleanup_decision_records(
            supabase_admin_client,
            manuscript_id,
            [eic.id, author.id],
        )
