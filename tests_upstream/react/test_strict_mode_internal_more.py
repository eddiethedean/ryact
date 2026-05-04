from __future__ import annotations

from ryact import StrictMode, create_element, use_state
from ryact.dev import set_dev
from ryact_testkit import create_noop_root


def test_should_default_to_not_strict() -> None:
    # Upstream: ReactStrictMode-test.internal.js
    # "should default to not strict"
    #
    # In Ryact, StrictMode behavior is DEV-gated.
    set_dev(False)
    calls = {"n": 0}
    root = create_noop_root()

    def App() -> object:
        calls["n"] += 1
        _v, _set_v = use_state(0)
        return create_element("div")

    root.render(create_element(StrictMode, None, create_element(App)))
    assert calls["n"] == 1
