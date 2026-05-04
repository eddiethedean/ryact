from __future__ import annotations

from ryact import create_element, use_ref
from ryact.hooks import RefObject
from ryact_testkit import create_noop_root


def test_useref_creates_ref_object_initialized_with_provided_value() -> None:
    # Upstream: useRef-test.internal.js
    # "creates a ref object initialized with the provided value"
    root = create_noop_root()
    seen: list[RefObject] = []

    def App() -> object:
        r = use_ref(123)
        seen.append(r)
        return None

    root.render(create_element(App, {}))
    assert len(seen) == 1
    assert seen[0]["current"] == 123


def test_useref_returns_same_ref_across_rerenders_and_ignores_new_initial() -> None:
    # Upstream: useRef-test.internal.js
    # "should return the same ref during re-renders"
    root = create_noop_root()
    seen: list[RefObject] = []

    initial: object = "first"

    def App() -> object:
        r = use_ref(initial)
        seen.append(r)
        return None

    root.render(create_element(App, {}))
    initial = "second"
    root.render(create_element(App, {}))

    assert len(seen) == 2
    assert seen[0] is seen[1]
    assert seen[1]["current"] == "first"
