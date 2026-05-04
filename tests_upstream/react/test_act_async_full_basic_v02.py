from __future__ import annotations

from typing import Any

from ryact import create_element
from ryact_testkit import act_async, create_noop_root, queue_microtask


def _div(text: str) -> Any:
    return create_element("div", {"text": text})


def test_act_async_drains_microtasks_and_flushes() -> None:
    root = create_noop_root()
    seen: list[str] = []

    async def work() -> None:
        root.render(_div("a"))
        queue_microtask(lambda: seen.append("m1"))

    # Enable act environment to avoid dev warning spam in translated suites.
    from ryact_testkit import set_act_environment_enabled

    set_act_environment_enabled(True)
    act_async(work, flush=root.flush, max_microtasks=2)
    assert "m1" in seen
    assert root.get_children_snapshot()["props"]["text"] == "a"

