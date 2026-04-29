from __future__ import annotations

from typing import Any

import pytest

from ryact import create_element, use
from ryact.concurrent import Thenable, suspense
from ryact_testkit import create_noop_root


def _text(value: str) -> Any:
    return create_element("span", {"text": value})


def test_basic_use_promise() -> None:
    # Upstream: ReactUse-test.js
    # "basic use(promise)"
    t: Thenable = Thenable()

    def App() -> Any:
        value = use(t)
        return _text(str(value))

    root = create_noop_root()
    root.render(
        suspense(
            fallback=create_element("div", {"text": "Loading"}),
            children=create_element(App),
        )
    )
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "Loading"

    t.resolve("A")
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "A"


def test_unwraps_thenable_that_fulfills_synchronously_without_suspending() -> None:
    # Upstream: ReactUse-test.js
    # "unwraps thenable that fulfills synchronously without suspending"
    t: Thenable = Thenable()
    t.resolve("OK")

    def App() -> Any:
        return _text(str(use(t)))

    root = create_noop_root()
    root.render(create_element(App))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "OK"


def test_using_a_rejected_promise_will_throw() -> None:
    # Upstream: ReactUse-test.js
    # "using a rejected promise will throw"
    t: Thenable = Thenable()
    t.reject(RuntimeError("nope"))

    def App() -> Any:
        return _text(str(use(t)))

    root = create_noop_root()
    with pytest.raises(RuntimeError, match="nope"):
        root.render(create_element(App))

