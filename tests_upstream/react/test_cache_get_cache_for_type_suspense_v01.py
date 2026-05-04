from __future__ import annotations

from typing import Any

from ryact import create_element, unstable_getCacheForType
from ryact.concurrent import Suspend, Thenable, suspense
from ryact_testkit import create_noop_root


def _span(text: str) -> Any:
    return create_element("span", {"text": text})


def test_get_cache_for_type_is_scoped_to_render_attempt_and_survives_suspense_retry() -> None:
    # Minimal acceptance slice for reopening Suspense/noop cache-driven suites.
    thenable = Thenable()
    state = {"ready": False}

    created: list[int] = []

    class Box:
        def __init__(self) -> None:
            created.append(1)

    def factory() -> Box:
        return Box()

    def App() -> Any:
        _ = unstable_getCacheForType(factory)
        if not state["ready"]:
            raise Suspend(thenable)
        return _span("done")

    root = create_noop_root()
    root.render(suspense(fallback=_span("loading"), children=create_element(App)))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "loading"
    assert len(created) >= 1

    state["ready"] = True
    thenable.resolve()
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "done"

