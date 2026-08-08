"""Export the OpenAPI schema to a file.

The frontend's TypeScript types are generated from this, so the two sides of the
monorepo cannot drift apart silently.

Usage::

    python -m bharat_os.scripts.export_openapi ../openapi.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python -m bharat_os.scripts.export_openapi <output.json>", file=sys.stderr)
        return 2

    from bharat_os.main import create_app

    destination = Path(argv[1])
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(create_app().openapi(), indent=2) + "\n", encoding="utf-8")
    print(f"wrote {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
