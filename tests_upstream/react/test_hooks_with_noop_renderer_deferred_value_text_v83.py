from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from ryact import create_element, use_deferred_value, use_state
from ryact_testkit import act, create_noop_root, set_act_environment_enabled


@pytest.mark.asyncio
async def test_defers_text_value() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "defers text value"
    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        setter: list[Callable[[str], None] | None] = [None]

        def App() -> Any:
            text, set_text = use_state("A")
            setter[0] = set_text
            deferred = use_deferred_value(text)
            return create_element(
                "div",
                {"text": text, "deferred": deferred},
            )

        with act(flush=root.flush):
            root.render(create_element(App))
        snap0 = root.get_children_snapshot()
        assert isinstance(snap0, dict)
        assert snap0["props"]["text"] == "A"
        assert snap0["props"]["deferred"] == "A"

        set_text = setter[0]
        assert set_text is not None
        set_text("B")

        # Commit the update; deferred value should lag until a later flush.
        root.flush()
        snap1 = root.get_children_snapshot()
        assert isinstance(snap1, dict)
        assert snap1["props"]["text"] == "B"
        assert snap1["props"]["deferred"] == "A"

        root.flush()
        snap2 = root.get_children_snapshot()
        assert isinstance(snap2, dict)
        assert snap2["props"]["text"] == "B"
        assert snap2["props"]["deferred"] == "B"
    finally:
        set_act_environment_enabled(False)
