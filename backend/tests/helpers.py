"""Shared helpers for tests.

Kept separate from the test modules so importing a fixture never drags in
another module's tests.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

PASSWORD = "correct-horse-battery-staple"
EMAIL = "founder@example.com"

#: A complete, valid profile including both sensitive fields.
VALID_PROFILE: dict = {
    "entity_name": "Test Labs Private Limited",
    "state": "Maharashtra",
    "sector": "edtech",
    "stage": "early",
    "employee_count": 8,
    "registrations": ["dpiit"],
    "annual_turnover_inr": 1200000,
    "social_category": "general",
}

TURNOVER: int = VALID_PROFILE["annual_turnover_inr"]


def register(
    client: TestClient,
    *,
    email: str = EMAIL,
    consents: list[str] | None = None,
):
    """Register an account and leave the session cookie on ``client``."""
    return client.post(
        "/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "consents": consents if consents is not None else ["scheme_matching"],
        },
    )
