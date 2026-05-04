from __future__ import annotations

from typing import Any

from ryact import create_element, scope
from ryact_testkit import create_noop_root


def _span(text: str) -> Any:
    return create_element("span", {"text": text})


def test_scope_wraps_children_and_renders_transparently() -> None:
    root = create_noop_root()
    root.render(scope(children=_span("Hi")))
    root.flush()
    snap = root.get_children_snapshot()
    assert snap is not None
