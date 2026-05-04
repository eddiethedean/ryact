from __future__ import annotations

from typing import Any

from ryact import Component, create_element
from ryact.hooks import get_legacy_context
from ryact_testkit import create_noop_root


def _div(text: str) -> Any:
    return create_element("div", {"text": text})


def test_legacy_context_types_propagate_to_function_component() -> None:
    def Child() -> Any:
        ctx = get_legacy_context()
        return _div(str(ctx.get("foo")))

    Child.contextTypes = {"foo": object()}  # type: ignore[attr-defined]

    class Parent(Component):
        childContextTypes = {"foo": object()}

        def getChildContext(self) -> dict[str, Any]:  # noqa: N802
            return {"foo": 123}

        def render(self) -> Any:
            return create_element(Child)

    root = create_noop_root()
    root.render(create_element(Parent))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "123"

