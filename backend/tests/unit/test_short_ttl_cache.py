from __future__ import annotations

import time

from app.core.short_ttl_cache import ShortTTLCache


def test_short_ttl_cache_set_get_and_expire():
    cache: ShortTTLCache[dict[str, int]] = ShortTTLCache(max_entries=64)
    cache.set("k1", {"v": 1}, ttl_sec=0.2)
    assert cache.get("k1") == {"v": 1}
    time.sleep(0.25)
    assert cache.get("k1") is None


def test_short_ttl_cache_respects_max_entries():
    cache: ShortTTLCache[int] = ShortTTLCache(max_entries=32)
    for i in range(40):
        cache.set(f"k{i}", i, ttl_sec=5)
    # 不要求保留全部旧 key，但新 key 应可读取
    assert cache.get("k39") == 39


def test_short_ttl_cache_clear():
    cache: ShortTTLCache[int] = ShortTTLCache(max_entries=64)
    cache.set("k", 1, ttl_sec=5)
    assert cache.get("k") == 1
    cache.clear()
    assert cache.get("k") is None

