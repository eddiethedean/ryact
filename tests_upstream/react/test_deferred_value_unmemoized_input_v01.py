from __future__ import annotations

from ryact import create_element, use_deferred_value, use_state
from ryact.concurrent import start_transition
from ryact_testkit import create_noop_root


def test_unmemoized_input_does_not_infinite_loop_and_defers_on_urgent_update() -> None:
    # Upstream: ReactDeferredValue-test.js
    # "does not cause an infinite defer loop if the original value isn't memoized"
    renders: list[int] = [0]

    def App() -> object:
        renders[0] += 1
        v, set_v = use_state(1)
        # Fresh dict every render (like `useDeferredValue({value})` in JS).
        deferred = use_deferred_value({"value": v})
        return create_element(
            "div",
            {
                "urgent": v,
                "deferred": deferred["value"],
                "set": set_v,
            },
        )

    root = create_noop_root()
    root.render(create_element(App))
    for _ in range(12):
        if renders[0] > 30:
            break
        root.flush()

    assert renders[0] <= 30, "expected a bounded number of renders (no infinite defer loop)"

    c = root.container.last_committed
    assert c is not None
    assert c["props"]["urgent"] == 1
    assert c["props"]["deferred"] == 1

    set_v = c["props"]["set"]
    set_v(2)
    root.flush()
    c2 = root.container.last_committed
    assert c2 is not None
    assert c2["props"]["urgent"] == 2
    assert c2["props"]["deferred"] == 1

    root.flush()
    c3 = root.container.last_committed
    assert c3 is not None
    assert c3["props"]["urgent"] == 2
    assert c3["props"]["deferred"] == 2


def test_unmemoized_input_does_not_defer_inside_transition() -> None:
    renders: list[int] = [0]

    def App() -> object:
        renders[0] += 1
        v, set_v = use_state(2)
        deferred = use_deferred_value({"value": v})
        return create_element(
            "div",
            {
                "urgent": v,
                "deferred": deferred["value"],
                "set": set_v,
            },
        )

    root = create_noop_root()
    root.render(create_element(App))
    root.flush()
    c = root.container.last_committed
    assert c is not None
    set_v = c["props"]["set"]

    start_transition(lambda: set_v(3))
    root.flush()
    for _ in range(8):
        if renders[0] > 24:
            break
        root.flush()

    assert renders[0] <= 24
    c2 = root.container.last_committed
    assert c2 is not None
    assert c2["props"]["urgent"] == 3
    assert c2["props"]["deferred"] == 3
