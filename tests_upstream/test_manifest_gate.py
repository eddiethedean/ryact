from __future__ import annotations

import json
from pathlib import Path


def test_manifest_has_no_untracked_nonimplemented_tests() -> None:
    manifest_path = Path(__file__).parent / "MANIFEST.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    tests = data["tests"]
    assert isinstance(tests, list)
    for t in tests:
        assert t["status"] == "implemented", f"Non-implemented test in manifest: {t}"
