from __future__ import annotations

import json
from pathlib import Path

# Keep in sync with scripts/scheduler_jest_extract.SCHEDULER_TEST_FILES (ty does not load scripts/).
SCHEDULER_TEST_FILES = [
    "packages/scheduler/src/__tests__/Scheduler-test.js",
    "packages/scheduler/src/__tests__/SchedulerMock-test.js",
    "packages/scheduler/src/__tests__/SchedulerPostTask-test.js",
    "packages/scheduler/src/__tests__/SchedulerProfiling-test.js",
    "packages/scheduler/src/__tests__/SchedulerSetImmediate-test.js",
    "packages/scheduler/src/__tests__/SchedulerSetTimeout-test.js",
]

_INVENTORY = Path(__file__).parent / "upstream_inventory.json"
_MANIFEST = Path(__file__).parent.parent / "MANIFEST.json"


def _inventory() -> dict:
    return json.loads(_INVENTORY.read_text(encoding="utf-8"))


def _manifest() -> dict:
    return json.loads(_MANIFEST.read_text(encoding="utf-8"))


def test_inventory_schema_version() -> None:
    data = _inventory()
    assert data.get("schema_version") == 1
    assert data.get("upstream_repo") == "facebook/react"
    assert isinstance(data.get("upstream_ref"), str)
    cases = data["cases"]
    assert isinstance(cases, list)
    assert len(cases) > 0


def test_inventory_ids_unique() -> None:
    cases = _inventory()["cases"]
    ids = [c["id"] for c in cases]
    assert len(ids) == len(set(ids)), f"duplicate ids: {len(ids) - len(set(ids))}"


def test_inventory_upstream_paths_allowed() -> None:
    allowed = set(SCHEDULER_TEST_FILES)
    for c in _inventory()["cases"]:
        assert c["upstream_path"] in allowed, c["upstream_path"]


def test_inventory_case_fields() -> None:
    for c in _inventory()["cases"]:
        assert "id" in c and isinstance(c["id"], str)
        assert "describe_path" in c and isinstance(c["describe_path"], list)
        assert all(isinstance(x, str) for x in c["describe_path"])
        assert "it_title" in c and isinstance(c["it_title"], str)
        assert c["kind"] in ("it", "it.skip", "test")
        assert c["status"] in ("pending", "implemented", "non_goal")
        if c["status"] == "non_goal":
            assert c.get("non_goal_rationale"), f"non_goal without rationale: {c['id']}"
        if c["status"] == "implemented":
            assert c.get("manifest_id"), f"implemented without manifest_id: {c['id']}"
            assert c.get("python_test"), f"implemented without python_test: {c['id']}"


def test_implemented_manifest_ids_exist() -> None:
    manifest_ids = {t["id"] for t in _manifest()["tests"]}
    for c in _inventory()["cases"]:
        if c["status"] != "implemented":
            continue
        assert c["manifest_id"] in manifest_ids, c["manifest_id"]


def test_scheduler_browser_manifest_rows_have_inventory_coverage() -> None:
    """Every ``scheduler.browser.*`` manifest row must be backed by inventory cases."""
    inv = _inventory()
    by_manifest: dict[str, list[str]] = {}
    for c in inv["cases"]:
        if c["status"] != "implemented" or not c.get("manifest_id"):
            continue
        by_manifest.setdefault(c["manifest_id"], []).append(c["id"])
    for t in _manifest()["tests"]:
        mid = t["id"]
        if not mid.startswith("scheduler.browser"):
            continue
        assert by_manifest.get(mid), f"no inventory case with manifest_id {mid!r}"
