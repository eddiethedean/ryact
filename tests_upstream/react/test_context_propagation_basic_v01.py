from __future__ import annotations

from typing import Any

from ryact import Component, create_context, create_element
from ryact.context import context_provider
from ryact_testkit import create_noop_root
from ryact.wrappers import memo


def _span(text: str) -> Any:
    return create_element("span", {"text": text})


def test_memo_bailout_is_broken_by_context_change() -> None:
    # Acceptance slice: memo component must re-render if context it reads changes.
    cx = create_context("A")

    def Read() -> Any:
        from ryact.hooks import use_context

        v = use_context(cx)
        return _span(str(v))

    M = memo(Read)
    root = create_noop_root()
    root.render(context_provider(cx, "A", create_element(M)))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "A"

    root.render(context_provider(cx, "B", create_element(M)))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "B"


def test_class_contexttype_updates_through_provider() -> None:
    cx = create_context("A")

    class C(Component):
        contextType = cx  # type: ignore[misc,assignment]

        def render(self) -> object:
            return _span(str(self.context))

    root = create_noop_root()
    root.render(context_provider(cx, "A", create_element(C)))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "A"

    root.render(context_provider(cx, "B", create_element(C)))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "B"

