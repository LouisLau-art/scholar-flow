import socket


def test_matchmaking_paths_do_not_open_sockets(monkeypatch):
    """
    SC-002 审计（最小可验证版本）

    中文注释:
    - 该测试的目标不是禁止“系统内部依赖”（如 Supabase）本身的网络访问，
      而是确保 matchmaking 代码路径在单测可控输入下不会意外发起外网请求（例如 OpenAI）。
    - 因此这里使用全 mock 的 db_client + embedder，并禁用 socket 创建作为兜底告警。
    """

    monkeypatch.setenv("MATCHMAKING_MIN_REVIEWERS", "1")

    def deny_socket(*args, **kwargs):
        raise AssertionError("socket is disabled in this test")

    monkeypatch.setattr(socket, "socket", deny_socket)

    from unittest.mock import MagicMock

    from app.services.matchmaking_service import MatchmakingService

    class _Resp:
        def __init__(self, data):
            self.data = data

    db = MagicMock()

    t_embeddings = MagicMock()
    t_embeddings.select.return_value = t_embeddings
    t_embeddings.limit.return_value = t_embeddings
    t_embeddings.execute.return_value = _Resp([{"user_id": "u1"}])

    t_profiles = MagicMock()
    t_profiles.select.return_value = t_profiles
    t_profiles.in_.return_value = t_profiles
    t_profiles.execute.return_value = _Resp([{"id": "u1", "email": "x@example.com", "name": "X"}])

    def table(name: str):
        if name == "reviewer_embeddings":
            return t_embeddings
        if name == "user_profiles":
            return t_profiles
        raise AssertionError(name)

    db.table.side_effect = table

    rpc = MagicMock()
    rpc.execute.return_value = _Resp([{"user_id": "u1", "score": 0.9}])
    db.rpc.return_value = rpc

    svc = MatchmakingService(db_client=db, embedder=lambda _: [0.0] * 384)
    result = svc.analyze(manuscript_id=None, title="T", abstract="A")
    assert result["recommendations"][0]["match_score"] == 0.9

