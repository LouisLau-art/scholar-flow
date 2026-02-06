import os
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
import pytest
from fastapi import HTTPException

from app.core.security import create_magic_link_jwt, decode_magic_link_jwt


def test_magic_link_roundtrip(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("MAGIC_LINK_JWT_SECRET", "test-secret")
    reviewer_id = UUID("11111111-1111-1111-1111-111111111111")
    manuscript_id = UUID("22222222-2222-2222-2222-222222222222")
    assignment_id = UUID("33333333-3333-3333-3333-333333333333")

    token = create_magic_link_jwt(
        reviewer_id=reviewer_id,
        manuscript_id=manuscript_id,
        assignment_id=assignment_id,
        expires_in_days=14,
    )
    payload = decode_magic_link_jwt(token)
    assert payload.type == "magic_link"
    assert payload.reviewer_id == reviewer_id
    assert payload.manuscript_id == manuscript_id
    assert payload.assignment_id == assignment_id
    assert payload.exp > int(datetime.now(timezone.utc).timestamp())


def test_magic_link_tampered_token(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("MAGIC_LINK_JWT_SECRET", "test-secret")
    reviewer_id = UUID("11111111-1111-1111-1111-111111111111")
    manuscript_id = UUID("22222222-2222-2222-2222-222222222222")
    assignment_id = UUID("33333333-3333-3333-3333-333333333333")

    token = create_magic_link_jwt(
        reviewer_id=reviewer_id,
        manuscript_id=manuscript_id,
        assignment_id=assignment_id,
        expires_in_days=14,
    )
    tampered = token + "x"
    with pytest.raises(HTTPException) as e:
        decode_magic_link_jwt(tampered)
    assert e.value.status_code == 401


def test_magic_link_expired(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("MAGIC_LINK_JWT_SECRET", "test-secret")
    now = datetime.now(timezone.utc)
    exp = int((now - timedelta(days=15)).timestamp())

    token = jwt.encode(
        {
            "type": "magic_link",
            "reviewer_id": "11111111-1111-1111-1111-111111111111",
            "manuscript_id": "22222222-2222-2222-2222-222222222222",
            "assignment_id": "33333333-3333-3333-3333-333333333333",
            "exp": exp,
        },
        os.environ["MAGIC_LINK_JWT_SECRET"],
        algorithm="HS256",
    )

    with pytest.raises(HTTPException) as e:
        decode_magic_link_jwt(token)
    assert e.value.status_code == 401

