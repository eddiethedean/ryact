from __future__ import annotations

from typing import Any

from ryact import create_element
from ryact.concurrent import Suspend, Thenable, suspense
from ryact.use import use
from ryact_testkit import WarningCapture, create_noop_root


def test_warns_if_use_promise_is_wrapped_with_try_catch_block() -> None:
    # Upstream: ReactUse-test.js
    # "warns if use(promise) is wrapped with try/catch block"
    t = Thenable()

    def App() -> Any:
        try:
            v = use(t)
            return create_element("span", {"text": f"v={v}"})
        except Suspend:
            # Swallowing the suspension and returning normally should warn.
            return create_element("span", {"text": "caught"})

    root = create_noop_root()
    with WarningCapture() as wc:
        root.render(
            suspense(
                fallback=create_element("span", {"text": "loading"}),
                children=create_element(App),
            )
        )
        root.flush()
    wc.assert_any("try/catch")
    assert root.get_children_snapshot()["props"]["text"] == "caught"

