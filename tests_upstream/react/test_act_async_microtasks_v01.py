from __future__ import annotations

from ryact import act_async
from ryact_testkit import set_act_environment_enabled
from ryact_testkit.act import queue_microtask


def test_act_async_drains_microtasks() -> None:
    set_act_environment_enabled(True)
    seen: list[str] = []

    async def run() -> None:
        queue_microtask(lambda: seen.append("m1"))
        queue_microtask(lambda: seen.append("m2"))

    act_async(run, max_microtasks=5)
    assert seen == ["m1", "m2"]

