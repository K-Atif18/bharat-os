"""Load curated crawl sources — URLs the crawler should monitor for changes.

    python -m bharat_os.seed.load_crawl_sources

Safe to run repeatedly: a URL already present is left untouched rather than
duplicated or reset, so re-running this does not erase crawl history
(``last_content_hash``, ``consecutive_failures``) for a source already being
watched.

``scheme_slug`` on each entry is advisory, not a foreign key (see
:class:`bharat_os.models.crawl.CrawlSource`) — it is used only to route a
reviewer's attention, so a slug that does not match any current scheme is
logged but not treated as an error; the URL is still worth monitoring.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from sqlalchemy import select

from bharat_os.db import get_session_factory
from bharat_os.models.crawl import CrawlSource
from bharat_os.models.enums import CrawlSourceType
from bharat_os.models.scheme import Scheme

logger = logging.getLogger(__name__)

DATA_PATH = Path(__file__).parent / "data" / "crawl_sources.json"


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    entries = json.loads(DATA_PATH.read_text(encoding="utf-8"))

    created = 0
    skipped = 0

    with get_session_factory()() as session:
        known_slugs = set(session.scalars(select(Scheme.slug)))

        for entry in entries:
            url = entry["url"]
            existing = session.scalar(select(CrawlSource).where(CrawlSource.url == url))
            if existing is not None:
                skipped += 1
                continue

            scheme_slug = entry.get("scheme_slug")
            if scheme_slug and scheme_slug not in known_slugs:
                logger.warning(
                    "crawl source %s references unknown scheme slug %r "
                    "(will still be monitored)",
                    url,
                    scheme_slug,
                )

            session.add(
                CrawlSource(
                    url=url,
                    source_type=CrawlSourceType(entry["source_type"]),
                    scheme_slug=scheme_slug,
                )
            )
            created += 1

        session.commit()

    print(f"{created} crawl source(s) added, {skipped} already present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
