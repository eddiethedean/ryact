from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

import pytest
from ryact import create_element
from ryact_testkit import WarningCapture, act, create_noop_root, set_act_environment_enabled


@pytest.mark.asyncio
async def test_async_iterable_children() -> None:
    # Upstream: ReactUse-test.js
    # "async iterable children"
    async def gen() -> AsyncGenerator[Any, None]:
        yield create_element("span", {"text": "hi"})

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with WarningCapture() as wc, act(flush=root.flush):
            root.render(create_element("div", {"children": [gen()]}))
        wc.assert_any("Async iterable children are not supported")
        snap = root.get_children_snapshot()
        assert isinstance(snap, dict)
        assert snap["type"] == "div"
        # Unsupported child is dropped to None in the noop host.
        assert snap.get("children") == [None]
    finally:
        set_act_environment_enabled(False)
