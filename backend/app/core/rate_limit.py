from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from threading import Lock

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("scholarflow.rate_limit")


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    value = str(raw).strip().lower()
    return value in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int, *, minimum: int = 1) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(str(raw).strip())
    except Exception:
        return default
    return max(value, minimum)


def _is_test_env() -> bool:
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return True
    mode = (
        os.environ.get("GO_ENV")
        or os.environ.get("ENVIRONMENT")
        or os.environ.get("APP_ENV")
        or ""
    ).strip().lower()
    return mode in {"test", "testing"}


def is_rate_limit_enabled() -> bool:
    if _is_test_env():
        return False
    return _env_bool("RATE_LIMIT_ENABLED", True)


@dataclass(frozen=True)
class RateLimitPolicy:
    key: str
    max_requests: int
    window_sec: int


class _InMemoryRateLimiter:
    def __init__(self) -> None:
        self._entries: dict[str, tuple[int, float]] = {}
        self._lock = Lock()
        self._last_gc_at = time.monotonic()

    def _gc_if_needed(self, now: float) -> None:
        # 避免高并发下字典无限增长；每 60 秒清理一次过期 bucket。
        if now - self._last_gc_at < 60:
            return
        self._last_gc_at = now
        expired = [k for k, (_count, reset_at) in self._entries.items() if reset_at <= now]
        for k in expired:
            self._entries.pop(k, None)

    def hit(self, *, bucket: str, policy: RateLimitPolicy) -> tuple[bool, int, int]:
        now = time.monotonic()
        with self._lock:
            self._gc_if_needed(now)
            count, reset_at = self._entries.get(bucket, (0, now + policy.window_sec))
            if reset_at <= now:
                count = 0
                reset_at = now + policy.window_sec

            count += 1
            self._entries[bucket] = (count, reset_at)

            allowed = count <= policy.max_requests
            remaining = max(policy.max_requests - count, 0)
            retry_after = max(int(reset_at - now), 0)
            return allowed, remaining, retry_after


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    轻量内存限流中间件（按 IP + endpoint bucket）。

    中文注释:
    - 目标是给 Auth/MagicLink/Token 端点提供基础防刷保护；
    - 默认在非测试环境开启，可用环境变量关闭；
    - 多实例部署时为“实例内限流”，不等价于全局分布式限流。
    """

    def __init__(self, app) -> None:  # type: ignore[override]
        super().__init__(app)
        self._limiter = _InMemoryRateLimiter()
        self._global_policy = RateLimitPolicy(
            key="global",
            max_requests=_env_int("RATE_LIMIT_MAX_REQUESTS", 600),
            window_sec=_env_int("RATE_LIMIT_WINDOW_SEC", 60),
        )
        self._path_policies: list[tuple[str, RateLimitPolicy]] = [
            (
                "/api/v1/auth/dev-login",
                RateLimitPolicy(
                    key="auth_dev_login",
                    max_requests=_env_int("RATE_LIMIT_DEV_LOGIN_MAX", 12),
                    window_sec=_env_int("RATE_LIMIT_DEV_LOGIN_WINDOW_SEC", 60),
                ),
            ),
            (
                "/api/v1/auth/magic-link/verify",
                RateLimitPolicy(
                    key="auth_magic_verify",
                    max_requests=_env_int("RATE_LIMIT_MAGIC_VERIFY_MAX", 60),
                    window_sec=_env_int("RATE_LIMIT_MAGIC_VERIFY_WINDOW_SEC", 60),
                ),
            ),
            (
                "/api/v1/reviews/token/",
                RateLimitPolicy(
                    key="reviews_token",
                    max_requests=_env_int("RATE_LIMIT_REVIEWS_TOKEN_MAX", 120),
                    window_sec=_env_int("RATE_LIMIT_REVIEWS_TOKEN_WINDOW_SEC", 60),
                ),
            ),
            (
                "/api/v1/reviews/magic/assignments/",
                RateLimitPolicy(
                    key="reviews_magic",
                    max_requests=_env_int("RATE_LIMIT_REVIEWS_MAGIC_MAX", 180),
                    window_sec=_env_int("RATE_LIMIT_REVIEWS_MAGIC_WINDOW_SEC", 60),
                ),
            ),
        ]

    @staticmethod
    def _client_ip(request: Request) -> str:
        forwarded = (request.headers.get("x-forwarded-for") or "").strip()
        if forwarded:
            return forwarded.split(",")[0].strip() or "unknown"
        if request.client and request.client.host:
            return str(request.client.host)
        return "unknown"

    def _policy_for_path(self, path: str) -> RateLimitPolicy:
        for prefix, policy in self._path_policies:
            if path.startswith(prefix):
                return policy
        return self._global_policy

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        if request.method.upper() == "OPTIONS":
            return await call_next(request)

        path = request.url.path
        policy = self._policy_for_path(path)
        client_ip = self._client_ip(request)
        bucket = f"{policy.key}:{client_ip}"

        allowed, remaining, retry_after = self._limiter.hit(bucket=bucket, policy=policy)
        if not allowed:
            logger.warning(
                "Rate limit exceeded: path=%s ip=%s bucket=%s retry_after=%ss",
                path,
                client_ip,
                policy.key,
                retry_after,
            )
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests",
                    "type": "rate_limit_exceeded",
                    "retry_after": retry_after,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(policy.max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Window": str(policy.window_sec),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(policy.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Window"] = str(policy.window_sec)
        return response

