from unittest.mock import MagicMock

import pytest


class _Resp:
    def __init__(self, data):
        self.data = data


def _mk_db_for_analyze(*, corpus_rows, matches, profiles_rows):
    db = MagicMock()

    # reviewer_embeddings.select().limit().execute()
    t_embeddings = MagicMock()
    t_embeddings.select.return_value = t_embeddings
    t_embeddings.limit.return_value = t_embeddings
    t_embeddings.execute.return_value = _Resp(corpus_rows)

    # user_profiles.select().in_().execute()
    t_profiles = MagicMock()
    t_profiles.select.return_value = t_profiles
    t_profiles.in_.return_value = t_profiles
    t_profiles.execute.return_value = _Resp(profiles_rows)

    def table(name: str):
        if name == "reviewer_embeddings":
            return t_embeddings
        if name == "user_profiles":
            return t_profiles
        raise AssertionError(f"unexpected table {name}")

    db.table.side_effect = table

    rpc = MagicMock()
    rpc.execute.return_value = _Resp(matches)
    db.rpc.return_value = rpc
    return db


def test_analyze_cold_start_returns_insufficient_data():
    from app.services.matchmaking_service import MatchmakingService

    db = _mk_db_for_analyze(corpus_rows=[], matches=[], profiles_rows=[])
    svc = MatchmakingService(
        config=None,
        db_client=db,
        embedder=lambda _: [0.0] * 384,
    )
    result = svc.analyze(manuscript_id=None, title="t", abstract="a")
    assert result["insufficient_data"] is True
    assert result["recommendations"] == []


def test_analyze_success_calls_rpc_and_formats_output(monkeypatch):
    monkeypatch.setenv("MATCHMAKING_TOP_K", "5")
    monkeypatch.setenv("MATCHMAKING_THRESHOLD", "0.70")
    monkeypatch.setenv("MATCHMAKING_MIN_REVIEWERS", "1")

    from app.services.matchmaking_service import MatchmakingService

    db = _mk_db_for_analyze(
        corpus_rows=[{"user_id": "u1"}],
        matches=[{"user_id": "u1", "score": 0.9}],
        profiles_rows=[{"id": "u1", "email": "expert@example.com", "name": "Expert"}],
    )

    svc = MatchmakingService(
        db_client=db,
        embedder=lambda _: [0.0] * 384,
    )
    result = svc.analyze(manuscript_id=None, title="t", abstract=None)
    assert result["insufficient_data"] is False
    assert result["recommendations"][0]["email"] == "expert@example.com"
    assert result["recommendations"][0]["match_score"] == 0.9

    args, kwargs = db.rpc.call_args
    assert args[0] == "match_reviewers"
    payload = args[1]
    assert payload["query_embedding"].startswith("[")
    assert payload["query_embedding"].endswith("]")
