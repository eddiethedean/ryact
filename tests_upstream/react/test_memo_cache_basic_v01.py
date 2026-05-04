from __future__ import annotations

from typing import Any

from ryact import create_element
from ryact.hooks import use_memo
from ryact_testkit import create_noop_root


def _span(text: str) -> Any:
    return create_element("span", {"text": text})


def test_use_memo_reuses_value_across_rerenders_with_same_deps() -> None:
    calls: list[int] = []

    def App(*, x: int) -> Any:
        v = use_memo(lambda: (calls.append(1), x * 2)[1], (x,))
        return _span(str(v))

    root = create_noop_root()
    root.render(create_element(App, {"x": 1}))
    root.flush()
    root.render(create_element(App, {"x": 1}))
    root.flush()
    assert calls.count(1) == 1

