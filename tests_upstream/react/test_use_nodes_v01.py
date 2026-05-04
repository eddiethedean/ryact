from __future__ import annotations

from typing import Any

from ryact import create_context, create_element
from ryact.concurrent import Thenable, suspense
from ryact_testkit import create_noop_root


def _text(value: str) -> Any:
    return create_element("span", {"text": value})


def test_basic_context_as_node() -> None:
    # Upstream: ReactUse-test.js
    # "basic Context as node"
    ctx = create_context("A")

    def App() -> Any:
        # Render Context object directly as a node; renderer should unwrap to current value.
        return ctx

    root = create_noop_root()
    root.render(create_element(App))
    root.flush()
    assert root.get_children_snapshot() == "A"


def test_basic_promise_as_child() -> None:
    # Upstream: ReactUse-test.js
    # "basic promise as child"
    t: Thenable = Thenable()

    def App() -> Any:
        return create_element("div", None, t)

    root = create_noop_root()
    root.render(suspense(fallback=_text("Loading"), children=create_element(App)))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "Loading"

    t.resolve(_text("OK"))
    root.flush()
    assert root.get_children_snapshot()["children"][0]["props"]["text"] == "OK"


def test_context_as_node_at_the_root() -> None:
    # Upstream: ReactUse-test.js
    # "context as node, at the root"
    ctx = create_context("ROOT")
    root = create_noop_root()
    root.render(ctx)  # type: ignore[arg-type]
    root.flush()
    assert root.get_children_snapshot() == "ROOT"


def test_promise_resolves_to_a_context_rendered_as_a_node() -> None:
    # Upstream: ReactUse-test.js
    # "promises that resolves to a context, rendered as a node"
    ctx = create_context("C")
    t: Thenable = Thenable()

    def App() -> Any:
        return t

    root = create_noop_root()
    root.render(suspense(fallback=_text("Loading"), children=create_element(App)))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "Loading"

    t.resolve(ctx)
    root.flush()
    assert root.get_children_snapshot() == "C"
