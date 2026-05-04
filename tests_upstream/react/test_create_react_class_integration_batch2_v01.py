from __future__ import annotations

from typing import Any

from ryact import Component, create_element
from ryact.create_react_class import create_react_class
from ryact_testkit import WarningCapture, create_noop_root


def _div(text: str) -> Any:
    return create_element("div", {"text": text})


def test_supports_static_getderivedstatefromprops() -> None:
    def render(self: Any) -> Any:
        return _div(str(self.state.get("x")))

    def gdsfp(next_props: dict[str, Any], prev_state: dict[str, Any]) -> dict[str, Any] | None:
        return {"x": next_props["x"]}

    C = create_react_class({"render": render, "getDerivedStateFromProps": gdsfp})
    root = create_noop_root()
    root.render(create_element(C, {"x": 1}))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "1"
    root.render(create_element(C, {"x": 2}))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "2"


def test_warns_if_state_not_initialized_before_gdsfp() -> None:
    class Bad(Component):
        def __init__(self, **props: Any) -> None:
            super().__init__(**props)
            # Deliberately violate invariant to trigger DEV warning path.
            self._state = None  # type: ignore[assignment]

        @staticmethod
        def getDerivedStateFromProps(_p: dict[str, Any], _s: dict[str, Any]) -> dict[str, Any] | None:  # noqa: N802
            return None

        def render(self) -> Any:
            return _div("x")

    root = create_noop_root()
    with WarningCapture() as wc:
        root.render(create_element(Bad))
        root.flush()
    wc.assert_any("State must be initialized before static getDerivedStateFromProps")


def test_warns_if_getsnapshotbeforeupdate_is_static() -> None:
    class Snap(Component):
        @staticmethod
        def getSnapshotBeforeUpdate() -> None:  # noqa: N802
            return None

        def render(self) -> Any:
            return _div("x")

    root = create_noop_root()
    with WarningCapture() as wc:
        root.render(create_element(Snap))
        root.flush()
    wc.assert_any("getSnapshotBeforeUpdate() must not be declared as a staticmethod")

