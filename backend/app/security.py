"""Bounded per-process request backstop and single-origin browser policy."""

from collections import OrderedDict, deque
from math import ceil
from threading import Lock
from time import monotonic

APP_CSP = (
    "default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
    "connect-src 'self'; img-src 'self' data:; font-src 'self'; "
    "base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
)
DOCS_CSP = (
    "default-src 'none'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "connect-src 'self'; img-src 'self' data: https://fastapi.tiangolo.com; "
    "base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
)
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Content-Security-Policy": APP_CSP,
}


class RequestLimiter:
    """Direct-peer sliding window; never trusts caller-supplied forwarding headers.

    This is a bounded local backstop. Shared quotas and trusted proxy identity
    belong at the selected hosting ingress, not in each function instance.
    """

    def __init__(self, limit: int, *, clock=monotonic, capacity: int = 2048):
        self.limit, self.clock, self.capacity = limit, clock, capacity
        self._clients: OrderedDict[str, deque] = OrderedDict()
        self._lock = Lock()

    def retry_after(self, peer: str) -> int | None:
        now = self.clock()
        with self._lock:
            requests = self._clients.pop(peer, deque())
            while requests and requests[0] <= now - 60:
                requests.popleft()
            self._clients[peer] = requests
            while len(self._clients) > self.capacity:
                self._clients.popitem(last=False)
            if len(requests) >= self.limit:
                return max(1, ceil(60 - (now - requests[0])))
            requests.append(now)
            return None
