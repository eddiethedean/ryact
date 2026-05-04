from __future__ import annotations

from typing import Any

from ryact import create_element, use_state
from ryact_testkit import act_call, create_noop_root, queue_microtask, set_act_environment_enabled


def _span(value: str) -> Any:
    return create_element("span", {"text": value})


def test_bypasses_queuemicrotask() -> None:
    # Upstream: ReactIsomorphicAct-test.js
    # "bypasses queueMicrotask"
    #
    # In JS, this asserts act() can flush promise continuations without relying on the host
    # queueMicrotask implementation. In ryact-testkit, we model this with a deterministic
    # microtask queue.
    set_act_environment_enabled(True)
    root = create_noop_root()
    setter_ref: list[Any] = [None]

    def App() -> Any:
        value, set_value = use_state("A")
        setter_ref[0] = set_value
        return _span(str(value))

    act_call(lambda: root.render(create_element(App)), flush=root.flush)
    assert root.container.last_committed["props"]["text"] == "A"

    def cb() -> None:
        def _microtask() -> None:
            set_value = setter_ref[0]
            set_value("B")

        queue_microtask(_microtask)

    act_call(cb, flush=root.flush, drain_microtasks=2)
    assert root.container.last_committed["props"]["text"] == "B"
