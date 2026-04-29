from __future__ import annotations

from ryact.dev import set_dev
from ryact_testkit import WarningCapture, act_call, set_act_environment_enabled


def test_behavior_in_production() -> None:
    # Upstream: ReactIsomorphicAct-test.js
    # "behavior in production"
    set_act_environment_enabled(False)
    set_dev(False)
    try:
        with WarningCapture() as cap:
            act_call(lambda: None)
        assert cap.messages == []
    finally:
        set_dev(True)

