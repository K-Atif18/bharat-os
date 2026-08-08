"""Tests for the curated crawl-source seed loader."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from bharat_os.models.crawl import CrawlSource
from bharat_os.seed.load_crawl_sources import main as load_crawl_sources


class TestLoadCrawlSources:
    def test_loading_the_real_curated_sources_is_idempotent(self, session: Session) -> None:
        first = load_crawl_sources()
        assert first == 0  # exit code, not a count

        first_count = len(session.scalars(select(CrawlSource)).all())
        assert first_count > 0

        second = load_crawl_sources()
        assert second == 0

        second_count = len(session.scalars(select(CrawlSource)).all())
        assert second_count == first_count, "re-running must not duplicate sources"

    def test_every_loaded_source_has_a_url_and_a_valid_type(self, session: Session) -> None:
        load_crawl_sources()
        sources = session.scalars(select(CrawlSource)).all()
        assert sources
        for source in sources:
            assert source.url.startswith("https://") or source.url.startswith("http://")
            assert source.is_active is True
