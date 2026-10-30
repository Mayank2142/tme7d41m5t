"""Bounded per-process request backstop and single-origin browser policy."""

import re
from collections import OrderedDict, deque
from math import ceil
from threading import Lock
from time import monotonic

from starlette.requests import Request

from backend.app.config import Settings

APP_CSP = (
    "default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
    "connect-src 'self'; img-src 'self' data:; font-src 'self'; "
    "base-uri 'none'; frame-ancestors 'none'; form-action 'self'; "
    "object-src 'none'; script-src-attr 'none'"
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
    "Cross-Origin-Resource-Policy": "same-origin",
    "X-DNS-Prefetch-Control": "off",
}


def request_problem(request: Request, settings: Settings) -> tuple[int, str, str] | None:
    """Reject unwanted traffic before filters, database reads, or cache lookups."""
    headers = request.scope["headers"]
    if len(headers) > 64 or sum(len(k) + len(v) for k, v in headers) > 16384:
        return 431, "HEADERS_TOO_LARGE", "Request headers exceed the supported size."
    if len(request.scope.get("raw_path", b"")) + len(request.scope["query_string"]) > 4096:
        return 414, "URI_TOO_LONG", "The request URL exceeds the supported size."
    hosts = request.headers.getlist("host")
    host_value = hosts[0].lower() if len(hosts) == 1 else ""
    host = host_value.split(":", 1)[0]
    if not re.fullmatch(r"[a-z0-9.-]+(?::[0-9]{1,5})?", host_value):
        return 400, "INVALID_HOST", "The request host is not allowed."
    if host not in settings.allowed_hosts:
        return 400, "INVALID_HOST", "The request host is not allowed."
    if request.method not in {"GET", "HEAD"}:
        return 405, "METHOD_NOT_ALLOWED", "This service supports read-only requests."
    lengths = request.headers.getlist("content-length")
    if len(lengths) > 1 or "transfer-encoding" in request.headers:
        return 400, "INVALID_REQUEST_BODY", "Request bodies are not supported."
    if lengths:
        if not lengths[0].isdigit():
            return 400, "INVALID_REQUEST_BODY", "Request bodies are not supported."
        if len(lengths[0]) > 10 or int(lengths[0]) != 0:
            return 413, "REQUEST_BODY_NOT_ALLOWED", "Request bodies are not supported."
    if (
        request.scope["path"].startswith("/api/")
        and request.headers.get("sec-fetch-site") == "cross-site"
    ):
        return 403, "CROSS_SITE_REQUEST", "Open the dashboard to access this resource."
    return None


class RequestLimiter:
    """Direct-peer sliding window; never trusts caller-supplied forwarding headers.

    This is a bounded local backstop. Shared quotas and trusted proxy identity
    belong at the selected hosting ingress, not in each function instance.
    """

    def __init__(self, limit: int, *, clock=monotonic, capacity: int = 2048):
        self.limit, self.clock = limit, clock
        # Bound timestamp storage too, even if an operator increases the quota.
        self.capacity = min(capacity, max(1, 131072 // limit))
        self._clients: OrderedDict[str, deque] = OrderedDict()
        self._lock = Lock()

    def retry_after(self, peer: str) -> int | None:
        now = self.clock()
        with self._lock:
            if peer not in self._clients and len(self._clients) >= self.capacity:
                for expired in [
                    key
                    for key, queue in self._clients.items()
                    if not queue or queue[-1] <= now - 60
                ]:
                    self._clients.pop(expired)
                # Never evict an active peer's quota to make room for new identities.
                if len(self._clients) >= self.capacity:
                    return 60
            requests = self._clients.pop(peer, deque())
            while requests and requests[0] <= now - 60:
                requests.popleft()
            self._clients[peer] = requests
            if len(requests) >= self.limit:
                return max(1, ceil(60 - (now - requests[0])))
            requests.append(now)
            return None
