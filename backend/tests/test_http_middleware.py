"""HTTP middleware protections and orchestrator health semantics."""

from __future__ import annotations

import json
import logging
import uuid

from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from bharat_os.db import get_db
from bharat_os.http_middleware import RequestContextMiddleware, current_request_id
from bharat_os.logging_config import JsonFormatter


class TestResponseProtections:
    def test_api_responses_include_security_headers(self, client: TestClient) -> None:
        response = client.get("/health/live")

        assert response.status_code == 200
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["x-frame-options"] == "DENY"
        assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
        assert response.headers["referrer-policy"] == "no-referrer"
        assert "camera=()" in response.headers["permissions-policy"]

    def test_valid_request_id_is_returned(self, client: TestClient) -> None:
        response = client.get("/health/live", headers={"X-Request-ID": "judge-demo-42"})
        assert response.headers["x-request-id"] == "judge-demo-42"

    def test_invalid_request_id_is_replaced(self, client: TestClient) -> None:
        response = client.get("/health/live", headers={"X-Request-ID": "bad id value"})
        generated = response.headers["x-request-id"]
        assert generated != "bad id value"
        uuid.UUID(generated)

    def test_production_responses_enable_hsts(self) -> None:
        async def endpoint(_request):  # type: ignore[no-untyped-def]
            return JSONResponse({"ok": True})

        app = Starlette(routes=[Route("/", endpoint)])
        app.add_middleware(RequestContextMiddleware, production=True)
        with TestClient(app) as client:
            response = client.get("/")

        assert response.headers["strict-transport-security"].startswith("max-age=63072000")


class TestRequestLogging:
    def test_json_logs_include_the_active_request_id(self) -> None:
        formatter = JsonFormatter()

        async def endpoint(_request):  # type: ignore[no-untyped-def]
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg="inside request",
                args=(),
                exc_info=None,
            )
            return JSONResponse(json.loads(formatter.format(record)))

        app = Starlette(routes=[Route("/", endpoint)])
        app.add_middleware(RequestContextMiddleware)
        with TestClient(app) as client:
            response = client.get("/", headers={"X-Request-ID": "trace-123"})

        assert response.json()["request_id"] == "trace-123"
        assert current_request_id() is None


class TestHealthProbes:
    def test_liveness_does_not_depend_on_database(self, client: TestClient) -> None:
        class UnavailableDatabase:
            def execute(self, _statement):  # type: ignore[no-untyped-def]
                raise SQLAlchemyError("database unavailable")

        def unavailable_db():  # type: ignore[no-untyped-def]
            yield UnavailableDatabase()

        client.app.dependency_overrides[get_db] = unavailable_db
        try:
            live = client.get("/health/live")
            ready = client.get("/health/ready")
        finally:
            client.app.dependency_overrides.pop(get_db, None)

        assert live.status_code == 200
        assert live.json() == {"status": "ok"}
        assert ready.status_code == 503
        assert ready.json()["database"] == "unreachable"
