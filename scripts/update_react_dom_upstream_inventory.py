#!/usr/bin/env python3
"""
Regenerate tests_upstream/react_dom/upstream_inventory.json from a facebook/react checkout.

Preserves status, manifest_id, python_test, non_goal_rationale, notes per canonical
(upstream_path + describe_path + it_title) when re-run.

Usage:
  python scripts/update_react_dom_upstream_inventory.py /path/to/react
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_INVENTORY_PATH = _REPO_ROOT / "tests_upstream" / "react_dom" / "upstream_inventory.json"
_MANIFEST_PATH = _REPO_ROOT / "tests_upstream" / "MANIFEST.json"


def _load_manifest_ids() -> set[str]:
    data = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    return {t["id"] for t in data.get("tests", []) if "id" in t}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "upstream_root",
        type=Path,
        help="Path to a facebook/react checkout (e.g. clone of github.com/facebook/react)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=_INVENTORY_PATH,
        help=f"Output JSON (default: {_INVENTORY_PATH})",
    )
    args = parser.parse_args()

    from scripts.react_dom_jest_extract import canonical_case_key, extract_all, stable_case_id

    upstream_ref = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8")).get(
        "upstream_ref", "main"
    )
    manifest_ids = _load_manifest_ids()

    old_cases: dict[str, dict] = {}
    if args.output.exists():
        old = json.loads(args.output.read_text(encoding="utf-8"))
        for row in old.get("cases", []):
            key = canonical_case_key(
                row["upstream_path"],
                tuple(row["describe_path"]),
                row["it_title"],
            )
            old_cases[key] = row

    extracted = extract_all(args.upstream_root.resolve())
    new_rows: list[dict] = []
    for ex in extracted:
        key = canonical_case_key(ex.upstream_path, ex.describe_path, ex.it_title)
        sid = stable_case_id(ex.upstream_path, ex.describe_path, ex.it_title)
        if key in old_cases:
            row = dict(old_cases[key])
            row["id"] = sid
            row["kind"] = ex.kind
            new_rows.append(row)
            continue
        row = {
            "id": sid,
            "upstream_path": ex.upstream_path,
            "describe_path": list(ex.describe_path),
            "it_title": ex.it_title,
            "kind": ex.kind,
            "status": "pending",
            "manifest_id": None,
            "python_test": None,
            "non_goal_rationale": None,
            "notes": None,
        }
        mid = row.get("manifest_id")
        if mid is not None and mid not in manifest_ids:
            print(f"Warning: manifest_id {mid!r} not in MANIFEST.json", file=sys.stderr)
        new_rows.append(row)

    new_keys = {
        canonical_case_key(ex.upstream_path, ex.describe_path, ex.it_title) for ex in extracted
    }
    for k in old_cases:
        if k not in new_keys:
            print(f"Note: upstream no longer has case {k[:120]}...", file=sys.stderr)

    doc = {
        "schema_version": 1,
        "upstream_repo": "facebook/react",
        "upstream_ref": upstream_ref,
        "cases": sorted(new_rows, key=lambda r: (r["upstream_path"], r["id"])),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(new_rows)} cases to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
