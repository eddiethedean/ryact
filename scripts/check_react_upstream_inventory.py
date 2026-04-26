#!/usr/bin/env python3
"""
Fail if facebook/react React-core __tests__ contain Jest cases not listed in
tests_upstream/react/upstream_inventory.json.

Usage:
  python scripts/check_react_upstream_inventory.py /path/to/react

Exit codes: 0 OK, 1 new upstream tests missing from inventory, 2 usage error.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_INVENTORY_PATH = _REPO_ROOT / "tests_upstream" / "react" / "upstream_inventory.json"


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "Usage: python scripts/check_react_upstream_inventory.py /path/to/facebook/react",
            file=sys.stderr,
        )
        return 2
    upstream_root = Path(sys.argv[1]).resolve()
    if not upstream_root.is_dir():
        print(f"Not a directory: {upstream_root}", file=sys.stderr)
        return 2

    # When executed as `python scripts/...`, sys.path[0] is the `scripts/` dir.
    # Ensure repo root is importable so `import scripts.*` works in CI.
    sys.path.insert(0, str(_REPO_ROOT))
    from scripts.react_jest_extract import canonical_case_key, extract_all

    if not _INVENTORY_PATH.is_file():
        print(f"Missing inventory: {_INVENTORY_PATH}", file=sys.stderr)
        return 1

    inv = json.loads(_INVENTORY_PATH.read_text(encoding="utf-8"))
    inv_keys: set[str] = set()
    for row in inv.get("cases", []):
        inv_keys.add(
            canonical_case_key(
                row["upstream_path"],
                tuple(row["describe_path"]),
                row["it_title"],
            )
        )

    extracted = extract_all(upstream_root)
    ext_keys = {
        canonical_case_key(ex.upstream_path, ex.describe_path, ex.it_title) for ex in extracted
    }

    missing = sorted(ext_keys - inv_keys)
    if missing:
        print("Upstream React-core tests not covered by upstream_inventory.json:", file=sys.stderr)
        for k in missing[:50]:
            print(f"  {k}", file=sys.stderr)
        if len(missing) > 50:
            print(f"  ... and {len(missing) - 50} more", file=sys.stderr)
        print(
            f"\nRun: python scripts/update_react_upstream_inventory.py {upstream_root}",
            file=sys.stderr,
        )
        return 1

    stale = sorted(inv_keys - ext_keys)
    for k in stale:
        print(f"Warning: inventory entry no longer in upstream extract: {k[:160]}", file=sys.stderr)

    print("OK: react upstream_inventory matches extracted Jest cases.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
