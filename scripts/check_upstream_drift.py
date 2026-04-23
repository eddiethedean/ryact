from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    """
    Drift checker scaffold.

    Usage:
      python scripts/check_upstream_drift.py /path/to/facebook/react

    It compares the manifest's referenced upstream test files to what's present
    in the upstream checkout. As we translate more tests, this becomes a hard gate.
    """

    if len(sys.argv) != 2:
        print("Usage: python scripts/check_upstream_drift.py /path/to/facebook/react")
        return 2

    upstream_root = Path(sys.argv[1]).resolve()
    manifest_path = Path(__file__).resolve().parents[1] / "tests_upstream" / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    missing = []  # type: List[str]
    for t in manifest.get("tests", []):
        rel = t.get("upstream_path")
        if not rel:
            continue
        if not (upstream_root / rel).exists():
            missing.append(rel)

    if missing:
        print("Missing upstream files referenced by manifest:")
        for m in missing:
            print(" - " + m)
        return 1

    print("OK: manifest upstream paths exist in provided upstream checkout.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
