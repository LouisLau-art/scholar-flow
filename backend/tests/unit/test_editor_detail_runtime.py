from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.api.v1.editor_detail_runtime import _authorize_manuscript_detail_access


def test_authorize_detail_access_allows_bound_academic_editor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.api.v1.editor_detail_runtime.ensure_manuscript_scope_access",
        lambda **_kwargs: "",
    )

    _authorize_manuscript_detail_access(
        manuscript_id="ms-1",
        manuscript={"academic_editor_id": "academic-1"},
        current_user={"id": "academic-1"},
        profile={"roles": ["academic_editor"]},
    )


def test_authorize_detail_access_rejects_unrelated_academic_editor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.api.v1.editor_detail_runtime.ensure_manuscript_scope_access",
        lambda **_kwargs: "",
    )

    with pytest.raises(HTTPException) as exc:
        _authorize_manuscript_detail_access(
            manuscript_id="ms-1",
            manuscript={"academic_editor_id": "academic-1"},
            current_user={"id": "academic-2"},
            profile={"roles": ["academic_editor"]},
        )

    assert exc.value.status_code == 403
