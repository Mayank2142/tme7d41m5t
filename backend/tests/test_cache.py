"""Concurrent cold loads, bounded retention, key isolation, and failure recovery."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event

import pytest

from backend.app.cache import BoundedCache


def test_concurrent_requests_share_one_cold_load():
    cache = BoundedCache(max_entries=2, max_bytes=100)
    ready, entered, release = Barrier(16), Event(), Event()
    calls = []

    def load():
        calls.append(1)
        entered.set()
        assert release.wait(5)
        return b"immutable"

    def request():
        ready.wait(timeout=5)
        return cache.get("release-cutoff-build", load, len)

    with ThreadPoolExecutor(max_workers=16) as pool:
        jobs = [pool.submit(request) for _ in range(16)]
        assert entered.wait(5)
        release.set()
        assert [job.result(timeout=5) for job in jobs] == [b"immutable"] * 16
    assert calls == [1] and not cache._pending


def test_lru_weight_expiry_oversized_values_and_failures():
    now = [0]
    cache = BoundedCache(max_entries=2, max_bytes=6, ttl=10, clock=lambda: now[0])

    def load(key, value):
        return cache.get(key, lambda: value, len)

    assert load("a", b"aaa") == b"aaa"
    assert load("b", b"bbb") == b"bbb"
    assert load("a", b"wrong") == b"aaa"
    load("c", b"ccc")
    assert set(cache._entries) == {"a", "c"} and cache._bytes == 6
    now[0] = 10
    assert load("a", b"new") == b"new" and set(cache._entries) == {"a"}
    assert load("large", b"1234567") == b"1234567" and "large" not in cache._entries

    def fail():
        raise RuntimeError("loader failed")

    with pytest.raises(RuntimeError, match="loader failed"):
        cache.get("failed", fail, len)
    assert not cache._pending and "failed" not in cache._entries
    assert load("failed", b"ok") == b"ok"
