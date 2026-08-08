"""Tests for crawl orchestration: LLM extraction wired into the crawl path,
and the reviewer-only API that triggers a run on demand.
"""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from bharat_os.crawler import runner as crawler_runner
from bharat_os.models.crawl import CrawlSource, PendingRevision
from bharat_os.models.enums import CrawlSourceType
from bharat_os.models.user import UserAccount
from helpers import register


def _make_reviewer(session: Session, client: TestClient) -> None:
    """Register a user via the client, then promote it to reviewer directly -
    there is no self-service path to reviewer status by design (see
    dependencies.require_reviewer), so a test must reach into the database.
    """
    response = register(client)
    account_id = uuid.UUID(response.json()["id"])
    account = session.get(UserAccount, account_id)
    assert account is not None
    account.is_reviewer = True
    session.commit()


def _seed_source(session: Session, url: str = "https://example.gov.in/scheme") -> CrawlSource:
    source = CrawlSource(url=url, source_type=CrawlSourceType.STATIC_HTML, scheme_slug=None)
    session.add(source)
    session.commit()
    session.refresh(source)
    return source


class TestCrawlSourceExtraction:
    """The crawler's own logic, exercised directly - not through the API,
    so these do not depend on reviewer auth at all."""

    def test_unchanged_content_produces_no_revision(
        self, session: Session, monkeypatch: object
    ) -> None:
        source = _seed_source(session)
        monkeypatch.setattr(crawler_runner, "is_allowed", lambda url: True)
        monkeypatch.setattr(crawler_runner, "_fetch", lambda src, limiter: "same content")

        first = crawler_runner.crawl_source(session, source)
        assert first.changed is True

        second = crawler_runner.crawl_source(session, source)
        assert second.changed is False

        revisions = session.scalars(select(PendingRevision)).all()
        assert len(revisions) == 1

    def test_changed_content_runs_extraction_and_queues_a_revision(
        self, session: Session, monkeypatch: object
    ) -> None:
        source = _seed_source(session)
        monkeypatch.setattr(crawler_runner, "is_allowed", lambda url: True)
        monkeypatch.setattr(
            crawler_runner,
            "_fetch",
            lambda src, limiter: "<html><body>New eligibility criteria apply.</body></html>",
        )

        outcome = crawler_runner.crawl_source(session, source)

        assert outcome.changed is True
        # The mock LLM provider does not know how to answer this request
        # shape (see structured_extraction's REQUIRED_KEYS vs MockProvider's
        # judgement-only responses) and degrades safely rather than
        # fabricating a plausible extraction - this asserts that degradation
        # actually happens, not that real extraction magically works offline.
        assert outcome.extraction_confidence == 0.0

        revision = session.scalars(select(PendingRevision)).one()
        assert revision.extraction_confidence == 0.0
        assert revision.extracted_content["requires_review"] is True
        assert "raw_html_excerpt" in revision.extracted_content

    def test_pdf_source_skips_extraction_and_keeps_raw_excerpt_only(
        self, session: Session, monkeypatch: object
    ) -> None:
        """PDF sources are handled by the dedicated PDF pipeline (ingest_pdf),
        not by this HTML-oriented path - the extraction step here is skipped
        for a source typed as PDF, and only the raw excerpt is kept."""
        source = CrawlSource(
            url="https://example.gov.in/notification.pdf",
            source_type=CrawlSourceType.PDF,
        )
        session.add(source)
        session.commit()
        session.refresh(source)

        monkeypatch.setattr(crawler_runner, "is_allowed", lambda url: True)
        # _fetch always returns str (fetch_static returns response.text); a PDF
        # source's underlying bytes are handled by the separate PDF pipeline
        # (pdf/pipeline.py's ingest_pdf), not by this crawl path.
        monkeypatch.setattr(crawler_runner, "_fetch", lambda src, limiter: "binary-pdf-marker")

        outcome = crawler_runner.crawl_source(session, source)

        assert outcome.changed is True
        assert outcome.extraction_confidence is None
        revision = session.scalars(select(PendingRevision)).one()
        assert "extracted_fields" not in revision.extracted_content

    def test_disallowed_by_robots_produces_no_revision(
        self, session: Session, monkeypatch: object
    ) -> None:
        source = _seed_source(session)
        monkeypatch.setattr(crawler_runner, "is_allowed", lambda url: False)

        outcome = crawler_runner.crawl_source(session, source)

        assert outcome.skipped_by_robots is True
        assert outcome.changed is False
        assert session.scalars(select(PendingRevision)).all() == []


class TestCrawlApi:
    def test_requires_reviewer_not_just_any_session(
        self, client: TestClient, session: Session
    ) -> None:
        register(client)  # a real session, but not a reviewer
        response = client.post("/crawler/run")
        assert response.status_code == 403

    def test_reviewer_can_trigger_a_run(
        self, client: TestClient, session: Session, monkeypatch: object
    ) -> None:
        _make_reviewer(session, client)
        monkeypatch.setattr(crawler_runner, "is_allowed", lambda url: True)
        monkeypatch.setattr(crawler_runner, "_fetch", lambda src, limiter: "unchanged content")
        source = _seed_source(session, url="https://example.gov.in/x")
        # Establish a baseline hash first, so the run triggered via the API
        # sees no change - keeps this test about the API contract, not about
        # re-testing extraction (already covered above).
        crawler_runner.crawl_source(session, source)

        response = client.post("/crawler/run")

        assert response.status_code == 200
        body = response.json()
        assert body["sources_crawled"] >= 1
        assert "outcomes" in body

    def test_reviewer_can_list_sources(self, client: TestClient, session: Session) -> None:
        _make_reviewer(session, client)
        _seed_source(session, url="https://example.gov.in/one")
        _seed_source(session, url="https://example.gov.in/two")

        response = client.get("/crawler/sources")
        assert response.status_code == 200
        urls = {row["url"] for row in response.json()}
        assert urls == {"https://example.gov.in/one", "https://example.gov.in/two"}
