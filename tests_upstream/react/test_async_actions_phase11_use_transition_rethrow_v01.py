from __future__ import annotations

from typing import Any

import pytest

from ryact import create_element, use_transition
from ryact.concurrent import Thenable
from ryact_testkit import create_noop_root


def _span(value: str) -> Any:
    return create_element("span", {"text": value})


def test_if_a_sync_action_throws_its_rethrown_from_use_transition() -> None:
    # Upstream: ReactAsyncActions-test.js
    # "if a sync action throws, it's rethrown from the `useTransition`"
    root = create_noop_root()
    start_ref: list[Any] = [None]

    def App() -> Any:
        _pending, start = use_transition()
        start_ref[0] = start
        return _span("ok")

    root.render(create_element(App))
    root.flush()

    start = start_ref[0]
    assert callable(start)

    def action() -> None:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        start(action)


def test_if_an_async_action_throws_its_rethrown_from_use_transition() -> None:
    # Upstream: ReactAsyncActions-test.js
    # "if an async action throws, it's rethrown from the `useTransition`"
    root = create_noop_root()
    start_ref: list[Any] = [None]
    t: Thenable = Thenable()

    def App() -> Any:
        _pending, start = use_transition()
        start_ref[0] = start
        return _span("ok")

    root.render(create_element(App))
    root.flush()

    start = start_ref[0]
    assert callable(start)

    def action() -> Thenable:
        return t

    _ = start(action)
    # Reject the async action; the rejection should surface on the next render/flush.
    t.reject(RuntimeError("async boom"))
    with pytest.raises(RuntimeError, match="async boom"):
        root.flush()

