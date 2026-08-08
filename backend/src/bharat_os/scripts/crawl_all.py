"""Run a crawl pass over every configured, active source.

    python -m bharat_os.scripts.crawl_all

For each monitored URL: check robots.txt, fetch, compare to the last known
content hash, and — for anything that changed — run LLM extraction and queue a
:class:`PendingRevision`. Nothing here writes to the live scheme corpus; see
:mod:`bharat_os.crawler.runner` for the enforced boundary. Review queued
changes with the reviewer-only ``/review-queue`` API or ``make`` (see
``review_queue.router``).

Exit code is 0 even when nothing changed — an unchanged source is a successful
crawl, not a failure. Exit code is 1 only if every configured source errored,
since that most likely means something is wrong with the crawler itself rather
than with any one government page.
"""

from __future__ import annotations

from bharat_os.crawler.runner import crawl_all
from bharat_os.db import get_session_factory


def main() -> int:
    with get_session_factory()() as session:
        outcomes = crawl_all(session)

        if not outcomes:
            print("No active crawl sources configured. Seed some with `make seed-crawl-sources`.")
            return 0

        changed = [o for o in outcomes if o.changed]
        skipped = [o for o in outcomes if o.skipped_by_robots]
        failed = [o for o in outcomes if o.error]

        for outcome in outcomes:
            if outcome.skipped_by_robots:
                print(f"  SKIP  {outcome.url}  (robots.txt disallows crawling)")
            elif outcome.error:
                print(f"  FAIL  {outcome.url}  ({outcome.error})")
            elif outcome.changed:
                confidence_note = (
                    f", extraction confidence {outcome.extraction_confidence:.2f}"
                    if outcome.extraction_confidence is not None
                    else ""
                )
                print(f"  CHANGED  {outcome.url}  -> queued for review{confidence_note}")
            else:
                print(f"  ok    {outcome.url}  (no change)")

        print()
        print(
            f"{len(outcomes)} source(s) crawled: "
            f"{len(changed)} changed, {len(skipped)} skipped by robots.txt, "
            f"{len(failed)} failed."
        )
        if changed:
            print("Review queued changes at GET /review-queue (reviewer access required).")

        return 1 if failed and len(failed) == len(outcomes) else 0


if __name__ == "__main__":
    raise SystemExit(main())
