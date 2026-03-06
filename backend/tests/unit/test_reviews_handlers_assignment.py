from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException, Response

from app.api.v1.reviews_handlers_assignment import (
    establish_reviewer_workspace_session_impl,
)


class _ReviewAssignmentsTableStub:
    def __init__(self, owner: "_SupabaseStub") -> None:
        self.owner = owner
        self._mode = "select"
        self._last_update_payload: dict[str, object] | None = None

    def select(self, *_args, **_kwargs):
        self._mode = "select"
        return self

    def update(self, payload: dict[str, object]):
        self._mode = "update"
        self._last_update_payload = dict(payload)
        self.owner.update_payloads.append(dict(payload))
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def single(self):
        return self

    def execute(self):
        if self._mode == "select":
            return SimpleNamespace(data=dict(self.owner.assignment))

        if self._mode == "update":
            if self.owner.update_errors:
                err = self.owner.update_errors.pop(0)
                if err is not None:
                    raise err
            return SimpleNamespace(data=[self._last_update_payload or {}])

        raise AssertionError(f"unsupported mode: {self._mode}")


class _SupabaseStub:
    def __init__(
        self,
        *,
        assignment: dict[str, str],
        update_errors: list[Exception | None] | None = None,
    ) -> None:
        self.assignment = assignment
        self.update_errors = list(update_errors or [])
        self.update_payloads: list[dict[str, object]] = []
        self._table = _ReviewAssignmentsTableStub(self)

    def table(self, name: str):
        assert name == "review_assignments"
        return self._table


@pytest.mark.asyncio
async def test_establish_workspace_session_redirects_unaccepted_assignment_to_invite() -> None:
    reviewer_id = str(uuid4())
    manuscript_id = str(uuid4())
    assignment_id = uuid4()
    stub = _SupabaseStub(
        assignment={
            "id": str(assignment_id),
            "reviewer_id": reviewer_id,
            "manuscript_id": manuscript_id,
            "status": "invited",
            "accepted_at": None,
        },
    )
    response = Response()

    out = await establish_reviewer_workspace_session_impl(
        assignment_id=assignment_id,
        response=response,
        current_user={"id": reviewer_id},
        supabase_admin_client=stub,
        create_magic_link_jwt_fn=lambda **_kwargs: "mock-token",
    )

    assert out["success"] is True
    assert out["data"]["redirect_url"] == f"/review/invite?assignment_id={assignment_id}"
    assert stub.update_payloads == []
    assert "sf_review_magic=mock-token" in (response.headers.get("set-cookie") or "")


@pytest.mark.asyncio
async def test_establish_workspace_session_uses_workspace_redirect_for_accepted_assignment() -> None:
    reviewer_id = str(uuid4())
    manuscript_id = str(uuid4())
    assignment_id = uuid4()
    stub = _SupabaseStub(
        assignment={
            "id": str(assignment_id),
            "reviewer_id": reviewer_id,
            "manuscript_id": manuscript_id,
            "status": "pending",
            "accepted_at": "2026-03-06T00:00:00Z",
        },
    )
    response = Response()

    out = await establish_reviewer_workspace_session_impl(
        assignment_id=assignment_id,
        response=response,
        current_user={"id": reviewer_id},
        supabase_admin_client=stub,
        create_magic_link_jwt_fn=lambda **_kwargs: "mock-token",
    )

    assert out["success"] is True
    assert out["data"]["redirect_url"] == f"/reviewer/workspace/{assignment_id}"
    assert stub.update_payloads == []
    assert "sf_review_magic=mock-token" in (response.headers.get("set-cookie") or "")
