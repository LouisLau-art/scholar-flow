from unittest.mock import MagicMock



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


def test_analyze_resolves_manuscript_from_id(monkeypatch):
    monkeypatch.setenv("MATCHMAKING_MIN_REVIEWERS", "1")

    from app.services.matchmaking_service import MatchmakingService

    db = MagicMock()

    # corpus preview
    t_embeddings = MagicMock()
    t_embeddings.select.return_value = t_embeddings
    t_embeddings.limit.return_value = t_embeddings
    t_embeddings.execute.return_value = _Resp([{"user_id": "u1"}])

    # manuscript fetch
    t_ms = MagicMock()
    t_ms.select.return_value = t_ms
    t_ms.eq.return_value = t_ms
    t_ms.single.return_value = t_ms
    t_ms.execute.return_value = _Resp({"title": "T", "abstract": "A"})

    # profiles fetch
    t_profiles = MagicMock()
    t_profiles.select.return_value = t_profiles
    t_profiles.in_.return_value = t_profiles
    t_profiles.execute.return_value = _Resp([{"id": "u1", "email": "e@example.com", "name": "E"}])

    # match rpc
    rpc = MagicMock()
    rpc.execute.return_value = _Resp([{"user_id": "u1", "score": 0.8}])
    db.rpc.return_value = rpc

    def table(name: str):
        if name == "reviewer_embeddings":
            return t_embeddings
        if name == "manuscripts":
            return t_ms
        if name == "user_profiles":
            return t_profiles
        raise AssertionError(name)

    db.table.side_effect = table

    svc = MatchmakingService(db_client=db, embedder=lambda _: [0.0] * 384)
    result = svc.analyze(
        manuscript_id="00000000-0000-0000-0000-000000000999",
        title=None,
        abstract=None,
    )
    assert result["recommendations"][0]["match_score"] == 0.8


def test_fetch_profiles_map_falls_back_when_columns_missing(monkeypatch):
    from app.services.matchmaking_service import MatchmakingService

    db = MagicMock()
    t = MagicMock()
    t.select.return_value = t
    t.in_.return_value = t

    # 第一次 select("id, email, name") 抛异常，触发降级分支
    t.execute.side_effect = [RuntimeError("missing column"), _Resp([{"id": "u1", "email": "x@example.com"}])]

    db.table.return_value = t
    svc = MatchmakingService(db_client=db, embedder=lambda _: [0.0] * 384)
    profiles = svc._fetch_profiles_map(["u1"])
    assert profiles["u1"]["email"] == "x@example.com"


def test_index_reviewer_skips_when_source_hash_unchanged(monkeypatch):
    from app.services.matchmaking_service import MatchmakingService

    # user_profiles：兴趣为空 + 没有历史 -> source_text = "General academic reviewer"
    t_profiles = MagicMock()
    t_profiles.select.return_value = t_profiles
    t_profiles.eq.return_value = t_profiles
    t_profiles.single.return_value = t_profiles
    t_profiles.execute.return_value = _Resp({"id": "u1", "research_interests": ""})

    # review_reports / manuscripts：不走
    t_rr = MagicMock()
    t_rr.select.return_value = t_rr
    t_rr.eq.return_value = t_rr
    t_rr.limit.return_value = t_rr
    t_rr.execute.return_value = _Resp([])

    # reviewer_embeddings：已有相同 hash -> 直接 return，不应触发 embedder/upsert
    from app.core.ml import hash_source_text

    expected_hash = hash_source_text("General academic reviewer")
    t_embeddings = MagicMock()
    t_embeddings.select.return_value = t_embeddings
    t_embeddings.eq.return_value = t_embeddings
    t_embeddings.single.return_value = t_embeddings
    t_embeddings.upsert.return_value = t_embeddings
    t_embeddings.execute.return_value = _Resp({"source_text_hash": expected_hash})

    db = MagicMock()

    def table(name: str):
        if name == "user_profiles":
            return t_profiles
        if name == "review_reports":
            return t_rr
        if name == "reviewer_embeddings":
            return t_embeddings
        if name == "manuscripts":
            raise AssertionError("should not query manuscripts")
        raise AssertionError(name)

    db.table.side_effect = table

    embedder = MagicMock()
    svc = MatchmakingService(db_client=db, embedder=embedder)
    svc.index_reviewer("u1")
    assert not embedder.called
    assert not t_embeddings.upsert.called


def test_index_reviewer_upserts_embedding_when_changed(monkeypatch):
    from app.services.matchmaking_service import MatchmakingService

    # user_profiles（含兴趣）
    t_profiles = MagicMock()
    t_profiles.select.return_value = t_profiles
    t_profiles.eq.return_value = t_profiles
    t_profiles.single.return_value = t_profiles
    t_profiles.execute.return_value = _Resp({"id": "u1", "research_interests": "NLP"})

    # review_reports：返回一个稿件 id
    t_rr = MagicMock()
    t_rr.select.return_value = t_rr
    t_rr.eq.return_value = t_rr
    t_rr.limit.return_value = t_rr
    t_rr.execute.return_value = _Resp([{"manuscript_id": "m1"}])

    # manuscripts：返回标题
    t_ms = MagicMock()
    t_ms.select.return_value = t_ms
    t_ms.in_.return_value = t_ms
    t_ms.execute.return_value = _Resp([{"id": "m1", "title": "Paper"}])

    # reviewer_embeddings：existing hash 不同 -> 会 upsert
    t_embeddings = MagicMock()
    t_embeddings.select.return_value = t_embeddings
    t_embeddings.eq.return_value = t_embeddings
    t_embeddings.single.return_value = t_embeddings
    t_embeddings.upsert.return_value = t_embeddings
    t_embeddings.execute.side_effect = [_Resp({"source_text_hash": "old"}), _Resp([])]

    db = MagicMock()

    def table(name: str):
        if name == "user_profiles":
            return t_profiles
        if name == "review_reports":
            return t_rr
        if name == "manuscripts":
            return t_ms
        if name == "reviewer_embeddings":
            return t_embeddings
        raise AssertionError(name)

    db.table.side_effect = table

    svc = MatchmakingService(db_client=db, embedder=lambda _: [0.0] * 384)
    svc.index_reviewer("u1")

    assert t_embeddings.upsert.called
    payload = t_embeddings.upsert.call_args.args[0]
    assert payload["user_id"] == "u1"
    assert payload["embedding"].startswith("[")
