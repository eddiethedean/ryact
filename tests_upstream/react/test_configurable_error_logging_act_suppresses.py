from __future__ import annotations

import pytest
from ryact import Component, create_element
from ryact_testkit import WarningCapture, act, create_noop_root, set_act_environment_enabled


def test_does_not_log_errors_when_inside_real_act() -> None:
    # Upstream: ReactConfigurableErrorLogging-test.js
    class Boom(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            raise RuntimeError("constructor error")

        def render(self) -> object:
            return create_element("div")

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with WarningCapture() as wc, pytest.raises(RuntimeError, match="constructor error"), act(root.flush):
            root.render(create_element(Boom))
        assert wc.messages == []
    finally:
        set_act_environment_enabled(False)
