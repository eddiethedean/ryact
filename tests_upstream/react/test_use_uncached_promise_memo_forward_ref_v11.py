from __future__ import annotations

from typing import Any

from ryact import create_element, forward_ref, memo, use
from ryact.concurrent import Thenable, suspense
from ryact_testkit import create_noop_root


def _text(value: str) -> Any:
    return create_element("span", {"text": value})


def test_unwrap_uncached_promises_inside_memo() -> None:
    # Upstream: ReactUse-test.js — "unwrap uncached promises inside memo"
    t = Thenable()

    def Inner() -> Any:
        v = use(t)
        return _text(str(v))

    M = memo(Inner)

    def App() -> Any:
        return suspense(
            fallback=_text("loading"),
            children=create_element(M),
        )

    root = create_noop_root()
    root.render(create_element(App))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "loading"

    t.resolve("memo-ok")
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "memo-ok"


def test_unwrap_uncached_promises_inside_forward_ref() -> None:
    # Upstream: ReactUse-test.js — "unwrap uncached promises inside forwardRef"
    t = Thenable()

    def render_fr(props: dict[str, Any], ref: object | None) -> Any:
        _ = props
        v = use(t)
        return _text(str(v))

    F = forward_ref(render_fr)

    def App() -> Any:
        return suspense(
            fallback=_text("loading"),
            children=create_element(F),
        )

    root = create_noop_root()
    root.render(create_element(App))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "loading"

    t.resolve("fr-ok")
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "fr-ok"
