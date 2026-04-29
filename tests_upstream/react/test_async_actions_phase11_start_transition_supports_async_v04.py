from __future__ import annotations

from ryact import start_transition
from ryact.concurrent import Thenable


def test_react_starttransition_supports_async_actions() -> None:
    # Upstream: ReactAsyncActions-test.js
    # "React.startTransition supports async actions"
    t = Thenable()

    def action() -> Thenable:
        return t

    ret = start_transition(action)
    assert ret is t

    # Should be able to settle after returning without error.
    t.resolve(None)

