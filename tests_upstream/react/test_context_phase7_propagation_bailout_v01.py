from __future__ import annotations

from typing import Any

from ryact import create_element
from ryact.context import create_context, context_provider
from ryact.wrappers import memo
from ryact_testkit import create_noop_root


def _span(value: str) -> Any:
    return create_element("span", {"text": value})


def test_context_change_should_prevent_bailout_of_memoized_component_memo_hoc() -> None:
    # Upstream: ReactContextPropagation-test.js
    # "context change should prevent bailout of memoized component (memo HOC)"
    Ctx = create_context("A")
    renders = {"count": 0}

    def Inner() -> Any:
        renders["count"] += 1
        return _span(Ctx._get())

    MemoInner = memo(Inner)
    root = create_noop_root()

    root.render(context_provider(Ctx, "A", create_element(MemoInner)))
    root.flush()
    assert renders["count"] == 1
    assert root.get_children_snapshot()["props"]["text"] == "A"

    # Same context value: memo can bail out.
    root.render(context_provider(Ctx, "A", create_element(MemoInner)))
    root.flush()
    assert renders["count"] == 1

    # New context value: must re-render even with equal props.
    root.render(context_provider(Ctx, "B", create_element(MemoInner)))
    root.flush()
    assert renders["count"] == 2
    assert root.get_children_snapshot()["props"]["text"] == "B"


def test_context_consumer_bails_out_if_context_hasnt_changed() -> None:
    # Upstream: ReactContextPropagation-test.js
    # "context consumer bails out if context hasn't changed"
    Ctx = create_context("A")
    renders = {"count": 0}

    def Inner() -> Any:
        renders["count"] += 1
        return _span(Ctx._get())

    MemoInner = memo(Inner)
    root = create_noop_root()

    root.render(context_provider(Ctx, "A", create_element(MemoInner)))
    root.flush()
    assert renders["count"] == 1

    # Re-rendering with same provider value should not re-run Inner.
    root.render(context_provider(Ctx, "A", create_element(MemoInner)))
    root.flush()
    assert renders["count"] == 1

