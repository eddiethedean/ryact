from __future__ import annotations

from typing import Any

import pytest
from ryact import create_element
from ryact.concurrent import Thenable, lazy, suspense
from ryact_testkit import create_noop_root


def _span(value: str) -> Any:
    return create_element("span", {"text": value})


def test_can_reject_synchronously_without_suspending() -> None:
    # Upstream: ReactLazy-test.internal.js
    # "can reject synchronously without suspending"
    root = create_noop_root()

    err = RuntimeError("nope")

    def loader() -> object:
        raise err

    LazyBad = lazy(loader)
    with pytest.raises(RuntimeError, match="nope"):
        root.render(create_element(LazyBad))


def test_suspends_until_module_has_loaded() -> None:
    # Upstream: ReactLazy-test.internal.js
    # "suspends until module has loaded"
    root = create_noop_root()
    t: Thenable = Thenable()

    def Inner() -> Any:
        return _span("Hi")

    def loader() -> Any:
        return t

    LazyInner = lazy(loader)

    root.render(
        suspense(
            fallback=_span("Loading"),
            children=create_element(LazyInner),
        )
    )
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "Loading"

    t.resolve({"default": Inner})
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "Hi"


def test_throws_if_promise_rejects() -> None:
    # Upstream: ReactLazy-test.internal.js
    # "throws if promise rejects"
    root = create_noop_root()
    t: Thenable = Thenable()

    def loader() -> Any:
        return t

    LazyInner = lazy(loader)
    root.render(
        suspense(
            fallback=_span("Loading"),
            children=create_element(LazyInner),
        )
    )
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "Loading"

    t.reject(RuntimeError("bad"))
    with pytest.raises(RuntimeError, match="bad"):
        root.flush()
