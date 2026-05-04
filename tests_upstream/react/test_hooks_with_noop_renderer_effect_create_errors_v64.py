from __future__ import annotations

from typing import Any

import pytest

from ryact import create_element, use_effect, use_state
from ryact_testkit import create_noop_root


def _span(value: str) -> Any:
    return create_element("span", {"text": value})


def test_handles_errors_in_create_on_mount() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "handles errors in create on mount"
    root = create_noop_root()

    def App() -> Any:
        def eff() -> Any:
            raise RuntimeError("create boom")

        use_effect(eff, ())
        return _span("ok")

    with pytest.raises(RuntimeError, match="create boom"):
        root.render(create_element(App))


def test_handles_errors_in_create_on_update() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "handles errors in create on update"
    root = create_noop_root()
    set_tick: list[Any] = [None]

    def App() -> Any:
        tick, set_t = use_state(0)
        set_tick[0] = set_t

        def eff() -> Any:
            if tick == 1:
                raise RuntimeError("create boom")
            return None

        use_effect(eff, (tick,))
        return _span(str(tick))

    root.render(create_element(App))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "0"

    set_tick[0](1)
    with pytest.raises(RuntimeError, match="create boom"):
        root.flush()

