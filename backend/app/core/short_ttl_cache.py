from __future__ import annotations

from threading import Lock
from time import monotonic
from typing import Generic, TypeVar

T = TypeVar("T")


class ShortTTLCache(Generic[T]):
    """
    轻量进程内短缓存（用于高频只读接口降压）。

    设计目标：
    - 简单可控：只支持 get/set/clear；
    - 线程安全：多请求并发下不会破坏字典状态；
    - 不跨进程：仅当前 worker 内生效，适用于秒级去抖。
    """

    def __init__(self, *, max_entries: int = 512) -> None:
        self._max_entries = max(32, int(max_entries or 512))
        self._store: dict[str, tuple[float, T]] = {}
        self._lock = Lock()

    def get(self, key: str) -> T | None:
        now = monotonic()
        with self._lock:
            row = self._store.get(key)
            if row is None:
                return None
            expires_at, value = row
            if expires_at <= now:
                self._store.pop(key, None)
                return None
            return value

    def set(self, key: str, value: T, *, ttl_sec: float) -> None:
        ttl = float(ttl_sec or 0)
        if ttl <= 0:
            return
        expires_at = monotonic() + ttl
        with self._lock:
            if len(self._store) >= self._max_entries:
                # 先清理过期条目；仍超限时按插入顺序淘汰最早项。
                now = monotonic()
                expired_keys = [k for k, (exp, _) in self._store.items() if exp <= now]
                for k in expired_keys:
                    self._store.pop(k, None)
                while len(self._store) >= self._max_entries:
                    try:
                        oldest_key = next(iter(self._store))
                    except StopIteration:
                        break
                    self._store.pop(oldest_key, None)
            self._store[key] = (expires_at, value)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

