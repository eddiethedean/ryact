#!/usr/bin/env python3
"""
Regenerate tests_upstream/scheduler/upstream_inventory.json from a facebook/react checkout.

Preserves status, manifest_id, python_test, non_goal_rationale, notes per canonical
(upstream_path + describe_path + it_title) when re-run.

Usage:
  python scripts/update_scheduler_upstream_inventory.py /path/to/react
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_INVENTORY_PATH = _REPO_ROOT / "tests_upstream" / "scheduler" / "upstream_inventory.json"
_MANIFEST_PATH = _REPO_ROOT / "tests_upstream" / "MANIFEST.json"

# Curated mapping: upstream Jest case -> manifest row for the current translated slice.
_MANIFEST_BY_CANONICAL_KEY: dict[str, dict[str, str | None]] = {
    json.dumps(
        {
            "path": "packages/scheduler/src/__tests__/Scheduler-test.js",
            "describe": ["SchedulerBrowser"],
            "title": "task that finishes before deadline",
        },
        sort_keys=True,
    ): {
        "manifest_id": "scheduler.browser.SchedulerBrowserParity",
        "python_test": "tests_upstream/scheduler/test_scheduler_browser_parity.py",
        "status": "implemented",
    },
    json.dumps(
        {
            "path": "packages/scheduler/src/__tests__/Scheduler-test.js",
            "describe": ["SchedulerBrowser"],
            "title": "multiple tasks",
        },
        sort_keys=True,
    ): {
        "manifest_id": "scheduler.browser.SchedulerBrowserParity",
        "python_test": "tests_upstream/scheduler/test_scheduler_browser_parity.py",
        "status": "implemented",
    },
    json.dumps(
        {
            "path": "packages/scheduler/src/__tests__/Scheduler-test.js",
            "describe": ["SchedulerBrowser"],
            "title": "multiple tasks with a yield in between",
        },
        sort_keys=True,
    ): {
        "manifest_id": "scheduler.browser.SchedulerBrowserParity",
        "python_test": "tests_upstream/scheduler/test_scheduler_browser_parity.py",
        "status": "implemented",
    },
    json.dumps(
        {
            "path": "packages/scheduler/src/__tests__/Scheduler-test.js",
            "describe": ["SchedulerBrowser"],
            "title": "cancels tasks",
        },
        sort_keys=True,
    ): {
        "manifest_id": "scheduler.browser.SchedulerBrowserParity",
        "python_test": "tests_upstream/scheduler/test_scheduler_browser_parity.py",
        "status": "implemented",
    },
    json.dumps(
        {
            "path": "packages/scheduler/src/__tests__/Scheduler-test.js",
            "describe": ["SchedulerBrowser"],
            "title": "task with continuation",
        },
        sort_keys=True,
    ): {
        "manifest_id": "scheduler.browser.SchedulerBrowserParity",
        "python_test": "tests_upstream/scheduler/test_scheduler_browser_parity.py",
        "status": "implemented",
    },
    json.dumps(
        {
            "path": "packages/scheduler/src/__tests__/Scheduler-test.js",
            "describe": ["SchedulerBrowser"],
            "title": "yielding continues in a new task regardless of how much time is remaining",
        },
        sort_keys=True,
    ): {
        "manifest_id": "scheduler.browser.SchedulerBrowserParity",
        "python_test": "tests_upstream/scheduler/test_scheduler_browser_parity.py",
        "status": "implemented",
    },
    json.dumps(
        {
            "path": "packages/scheduler/src/__tests__/Scheduler-test.js",
            "describe": ["SchedulerBrowser"],
            "title": "throws when a task errors then continues in a new event",
        },
        sort_keys=True,
    ): {
        "manifest_id": "scheduler.browser.SchedulerBrowserParity",
        "python_test": "tests_upstream/scheduler/test_scheduler_browser_parity.py",
        "status": "implemented",
    },
    json.dumps(
        {
            "path": "packages/scheduler/src/__tests__/Scheduler-test.js",
            "describe": ["SchedulerBrowser"],
            "title": "schedule new task after queue has emptied",
        },
        sort_keys=True,
    ): {
        "manifest_id": "scheduler.browser.SchedulerBrowserParity",
        "python_test": "tests_upstream/scheduler/test_scheduler_browser_parity.py",
        "status": "implemented",
    },
    json.dumps(
        {
            "path": "packages/scheduler/src/__tests__/Scheduler-test.js",
            "describe": ["SchedulerBrowser"],
            "title": "schedule new task after a cancellation",
        },
        sort_keys=True,
    ): {
        "manifest_id": "scheduler.browser.SchedulerBrowserParity",
        "python_test": "tests_upstream/scheduler/test_scheduler_browser_parity.py",
        "status": "implemented",
    },
}


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
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from scheduler_jest_extract import (
        canonical_case_key,
        extract_all,
        stable_case_id,
    )

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
        override = _MANIFEST_BY_CANONICAL_KEY.get(key)
        if override:
            mid = override.get("manifest_id")
            if mid not in manifest_ids:
                print(f"Warning: manifest_id {mid!r} not in MANIFEST.json", file=sys.stderr)
            row["manifest_id"] = mid
            row["python_test"] = override.get("python_test")
            row["status"] = override.get("status", "implemented")
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
