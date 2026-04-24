from __future__ import annotations

from ryact import use_deferred_value


def test_does_not_defer_during_a_transition() -> None:
    # Upstream: ReactDeferredValue-test.js
    # "does not defer during a transition"
    assert use_deferred_value("A") == "A"
