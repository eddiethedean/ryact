from __future__ import annotations

from ryact_testkit import WarningCapture, act, set_act_environment_enabled


def test_act_warns_if_the_environment_flag_is_not_enabled() -> None:
    # Upstream: ReactActWarnings-test.js
    # "act warns if the environment flag is not enabled"
    set_act_environment_enabled(False)
    with WarningCapture() as cap, act():
        pass
    assert any("not configured to support act" in str(rec.message).lower() for rec in cap.records)
