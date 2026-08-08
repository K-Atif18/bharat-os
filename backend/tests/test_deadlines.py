"""Deadline reachability calendar and ICS export."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from bharat_os.api.deadlines import _render_ics
from bharat_os.models.scheme import ApplicationWindow, Scheme, SchemeVersion
from bharat_os.schemas.deadlines import DeadlineCalendarOut, DeadlineOut
from bharat_os.services.deadlines import ReachabilityStatus
from helpers import VALID_PROFILE, register


def _seed_future_window(session: Session) -> SchemeVersion:
    close = datetime.now(UTC) + timedelta(days=45)
    version = SchemeVersion(
        scheme=Scheme(slug="future-grant"),
        version=1,
        is_current=True,
        name="Future, Growth; Grant",
        summary="A dated opportunity for calendar tests.",
        scheme_type="grant",
        status="active",
        administering_ministry="Ministry of Testing",
        target_segments=["startup"],
        sectors=[],
        states=[],
        benefit_description="Up to Rs 10 lakh.",
        application_difficulty="medium",
        drafting_lead_days=7,
        effective_from=datetime.now(UTC),
        windows=[
            ApplicationWindow(
                close_date=close,
                recurrence="one_time",
                notification_source="portal",
                source_url="https://example.gov.in/future-grant",
                source_quote="Applications close in 45 days.",
                last_verified_at=datetime.now(UTC),
                verified_by_human=True,
            )
        ],
    )
    session.add(version)
    session.commit()
    session.refresh(version)
    return version


class TestIcsRendering:
    def test_calendar_is_stable_and_escapes_text(self) -> None:
        deadline = DeadlineOut(
            scheme_id="00000000-0000-0000-0000-000000000001",
            scheme_version_id="00000000-0000-0000-0000-000000000002",
            slug="future-grant",
            name="Future, Growth; Grant",
            status=ReachabilityStatus.COMFORTABLE,
            close_date="2026-09-15",
            days_remaining=45,
            days_required=7,
            margin_days=38,
            bottleneck_document=None,
            bottleneck_days=None,
        )
        rendered = _render_ics(
            DeadlineCalendarOut(deadlines=[deadline], unreachable_count=0),
            generated_at=datetime(2026, 7, 31, 12, 0, tzinfo=UTC),
        )

        assert rendered.startswith("BEGIN:VCALENDAR\r\nVERSION:2.0")
        assert "DTSTAMP:20260731T120000Z" in rendered
        assert "DTSTART;VALUE=DATE:20260915" in rendered
        assert "DTEND;VALUE=DATE:20260916" in rendered
        assert "SUMMARY:Future\\, Growth\\; Grant application deadline" in rendered
        assert rendered.count("BEGIN:VALARM") == 4
        assert rendered.endswith("END:VCALENDAR\r\n")


class TestDeadlineCalendarApi:
    def test_export_requires_document_storage_consent(self, client: TestClient) -> None:
        register(client)
        client.put("/profile", json=VALID_PROFILE)

        response = client.get("/deadlines/calendar.ics")

        assert response.status_code == 403
        assert "document_storage" in response.text

    def test_exports_private_calendar_attachment(
        self, client: TestClient, session: Session
    ) -> None:
        register(client, consents=["scheme_matching", "document_storage"])
        client.put("/profile", json=VALID_PROFILE)
        version = _seed_future_window(session)

        response = client.get("/deadlines/calendar.ics")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/calendar")
        assert response.headers["cache-control"] == "private, no-store"
        assert "bharat-os-deadlines.ics" in response.headers["content-disposition"]
        assert f"UID:scheme-{version.id}@bharat-os" in response.text
        assert "Future\\, Growth\\; Grant application deadline" in response.text
