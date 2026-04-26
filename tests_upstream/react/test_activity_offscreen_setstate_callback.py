from __future__ import annotations

from typing import Any

from ryact import create_element
from ryact.component import Component
from ryact.concurrent import activity
from ryact_testkit import create_noop_root


def test_hidden_to_visible_reuse_includes_setstate_callback() -> None:
    """
    Upstream: Activity-test.js
    - when reusing old components (hidden -> visible), layout effects fire with same timing
      as if it were brand new (includes setState callback)
    """
    root = create_noop_root()
    log: list[str] = []
    sink: dict[str, Any] = {}

    class C(Component[dict[str, Any]]):
        def render(self) -> Any:
            sink["inst"] = self
            return create_element("div", {"id": "c"})

        def componentDidMount(self) -> None:  # noqa: N802
            log.append("didMount")

        def componentDidUpdate(self) -> None:  # noqa: N802
            log.append("didUpdate")

    # Mount visible.
    root.render(create_element(activity, {"mode": "visible", "children": create_element(C, {})}))
    assert log == ["didMount"]
    inst = sink["inst"]
    assert isinstance(inst, C)

    # Hide.
    root.render(create_element(activity, {"mode": "hidden", "children": create_element(C, {})}))

    # Queue a setState callback while hidden; it should not fire until reveal.
    inst.setState({"x": 1}, lambda: log.append("cb"))
    assert "cb" not in log

    # Reveal: should behave like a fresh visibility connect (no componentDidUpdate),
    # and flush the setState callback.
    root.render(create_element(activity, {"mode": "visible", "children": create_element(C, {})}))
    assert "didUpdate" not in log
    assert log[-1] == "cb"
