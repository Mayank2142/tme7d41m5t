"""Bounded process-local LRU with TTL and one loader per immutable cache key."""

from collections import OrderedDict
from collections.abc import Callable, Hashable
from concurrent.futures import Future
from threading import Lock
from time import monotonic

from backend.app.errors import ApiProblem


class BoundedCache[T]:
    def __init__(self, *, max_entries: int, max_bytes: int, ttl: float = 600, clock=monotonic):
        self.max_entries, self.max_bytes, self.ttl = max_entries, max_bytes, ttl
        self.clock = clock
        self._entries: OrderedDict[Hashable, tuple[float, int, T]] = OrderedDict()
        self._pending: dict[Hashable, Future[T]] = {}
        self._bytes = 0
        self._lock = Lock()

    def get(self, key: Hashable, load: Callable[[], T], weight: Callable[[T], int]) -> T:
        with self._lock:
            now = self.clock()
            for expired in [key for key, entry in self._entries.items() if entry[0] <= now]:
                self._bytes -= self._entries.pop(expired)[1]
            entry = self._entries.pop(key, None)
            if entry is not None:
                self._entries[key] = entry
                return entry[2]
            waiting = self._pending.get(key)
            if waiting is None:
                if len(self._pending) >= 64:
                    raise ApiProblem(503, "SERVER_BUSY", "The service is busy. Please retry.")
                waiting = self._pending[key] = Future()
                owner = True
            else:
                owner = False
        if not owner:
            return waiting.result()
        try:
            value = load()
            size = max(1, weight(value))
            with self._lock:
                if size <= self.max_bytes:
                    while self._entries and (
                        len(self._entries) >= self.max_entries
                        or self._bytes + size > self.max_bytes
                    ):
                        self._bytes -= self._entries.popitem(last=False)[1][1]
                    self._entries[key] = (self.clock() + self.ttl, size, value)
                    self._bytes += size
            waiting.set_result(value)
            return value
        except BaseException as exc:
            waiting.set_exception(exc)
            raise
        finally:
            with self._lock:
                self._pending.pop(key, None)
