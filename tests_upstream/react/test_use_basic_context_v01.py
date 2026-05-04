from __future__ import annotations

from typing import Any

from ryact import create_context, create_element, use
from ryact_testkit import create_noop_root


def test_basic_use_context() -> None:
    # Upstream: ReactUse-test.js
    # "basic use(context)"
    ctx = create_context("A")

    def App() -> Any:
        value = use(ctx)
        return create_element("div", {"text": value})

    root = create_noop_root()
    root.render(create_element(App))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "A"
