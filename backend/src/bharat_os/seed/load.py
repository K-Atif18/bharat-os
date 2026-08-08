"""Load the curated scheme corpus.

Usage::

    python -m bharat_os.seed.load

Safe to run repeatedly: unchanged schemes are left alone, changed schemes gain a
new version, and nothing is ever overwritten.
"""

from __future__ import annotations

import logging
import sys

from bharat_os.db import get_session_factory
from bharat_os.seed.loader import SeedDataError, load_from_disk


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        with get_session_factory()() as session:
            report = load_from_disk(session)
    except SeedDataError as exc:
        print(f"Seed data is invalid:\n  {exc}", file=sys.stderr)
        return 1

    print(report.summary())
    for slug in report.slugs_created:
        print(f"  + {slug}")
    for slug in report.slugs_versioned:
        print(f"  ^ {slug} (new version)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
