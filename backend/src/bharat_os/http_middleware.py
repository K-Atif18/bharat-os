"""HTTP request context and browser-facing response protections."""

from __future__ import annotations

import re
import uuid
from contextvars import ContextVar

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

_REQUEST_ID = ContextVar[str | None]("request_id", default=None)
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,128}$")

# The API serves JSON and FastAPI's interactive documentation. The CDN allowances
# are only for those documentation assets; user data is never loaded from them.
CONTENT_SECURITY_POLICY = "; ".join(
    (
        "default-src 'none'",
        "script-src 'self' https://cdn.jsdelivr.net",
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
        "img-src 'self' data: https://fastapi.tiangolo.com",
        "connect-src 'self'",
        "frame-ancestors 'none'",
        "base-uri 'none'",
        "form-action 'none'",
    )
)

SECURITY_HEADERS = {
    "content-security-policy": CONTENT_SECURITY_POLICY,
    "permissions-policy": "camera=(), geolocation=(), microphone=()",
    "referrer-policy": "no-referrer",
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
}


def current_request_id() -> str | None:
    """Return the request ID visible to the current async/thread context."""
    return _REQUEST_ID.get()


def _request_id(scope: Scope) -> str:
    for raw_name, raw_value in scope.get("headers", ()):
        if raw_name.lower() != b"x-request-id":
            continue
        candidate = raw_value.decode("latin-1")
        if _REQUEST_ID_PATTERN.fullmatch(candidate):
            return candidate
        break
    return str(uuid.uuid4())


class RequestContextMiddleware:
    """Attach a correlation ID and baseline security headers to every response."""

    def __init__(self, app: ASGIApp, *, production: bool = False) -> None:
        self.app = app
        self.production = production

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = _request_id(scope)
        token = _REQUEST_ID.set(request_id)

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers.setdefault("x-request-id", request_id)
                for name, value in SECURITY_HEADERS.items():
                    headers.setdefault(name, value)
                if self.production:
                    headers.setdefault(
                        "strict-transport-security",
                        "max-age=63072000; includeSubDomains",
                    )
            await send(message)

        try:
            await self.app(scope, receive, send_with_headers)
        finally:
            _REQUEST_ID.reset(token)
