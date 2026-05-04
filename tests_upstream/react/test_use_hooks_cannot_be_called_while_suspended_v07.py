from __future__ import annotations

import warnings
from typing import Any

import pytest
from ryact import create_element
from ryact.concurrent import Suspend, Thenable
from ryact.hooks import HookError, use_state
from ryact.use import use
from ryact_testkit import create_noop_root


def test_while_suspended_hooks_cannot_be_called_dispatcher_unset() -> None:
    # Upstream: ReactUse-test.js
    # "while suspended, hooks cannot be called (i.e. current dispatcher is unset correctly)"
    t = Thenable()

    def App() -> Any:
        try:
            _ = use(t)
        except Suspend:
            # If we caught the suspension, hooks must already be disabled.
            _state, _set_state = use_state(0)
            return create_element("span", {"text": "unreachable"})
        return create_element("span", {"text": "ok"})

    root = create_noop_root()
    # The noop host reports uncaught errors as RuntimeWarnings; filter those for this test.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        with pytest.raises(HookError, match="suspended"):
            root.render(create_element(App))
