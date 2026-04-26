#!/usr/bin/env python3
"""
Print pending / implemented / non_goal counts for React core + React DOM upstream inventories.

Usage:
  python scripts/report_upstream_inventory.py
  python scripts/report_upstream_inventory.py --top 40
  python scripts/report_upstream_inventory.py --json
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _summarize(inv_path: Path) -> dict:
    data = json.loads(inv_path.read_text(encoding="utf-8"))
    cases = data["cases"]
    by_status = Counter(c["status"] for c in cases)
    pending_by_path = Counter()
    for c in cases:
        if c["status"] == "pending":
            pending_by_path[c["upstream_path"]] += 1
    return {
        "path": str(inv_path.relative_to(_repo_root())),
        "total": len(cases),
        "by_status": dict(by_status),
        "pending_by_path": pending_by_path,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--top",
        type=int,
        default=30,
        metavar="N",
        help="show top N upstream_path buckets for pending (default: 30)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable JSON instead of text tables",
    )
    args = parser.parse_args()
    root = _repo_root()
    paths = [
        root / "tests_upstream/react/upstream_inventory.json",
        root / "tests_upstream/react_dom/upstream_inventory.json",
    ]
    summaries = [_summarize(p) for p in paths]
    if args.json:
        print(json.dumps(summaries, indent=2, sort_keys=True))
        return

    for s in summaries:
        print(f"=== {s['path']} ===")
        print(f"total cases: {s['total']}")
        for st in ("pending", "implemented", "non_goal"):
            n = s["by_status"].get(st, 0)
            print(f"  {st}: {n}")
        print(f"Top pending upstream_path (top {args.top}):")
        for path, n in s["pending_by_path"].most_common(args.top):
            print(f"  {n:5d}  {path}")
        print()


if __name__ == "__main__":
    main()
