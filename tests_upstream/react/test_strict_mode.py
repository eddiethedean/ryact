from __future__ import annotations

from ryact import StrictMode, create_element, use_state
from ryact.dev import set_dev
from ryact_testkit import create_noop_root


def test_double_invokes_components_with_hooks_in_strict_mode() -> None:
    # Upstream: ReactHooks-test.internal.js
    # "double-invokes components with Hooks in Strict Mode"
    set_dev(True)
    root = create_noop_root()
    calls = {"n": 0}

    def App() -> object:
        calls["n"] += 1
        _v, _set_v = use_state(0)
        return create_element("div")

    root.render(create_element(StrictMode, None, create_element(App)))
    assert calls["n"] == 2
