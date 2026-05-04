from __future__ import annotations

from ryact_testkit import act_call, set_act_environment_enabled


def test_return_value_sync_callback() -> None:
    # Upstream: ReactIsomorphicAct-test.js
    # "return value – sync callback"
    set_act_environment_enabled(True)
    assert act_call(lambda: "ok") == "ok"


def test_return_value_sync_callback_nested() -> None:
    # Upstream: ReactIsomorphicAct-test.js
    # "return value – sync callback, nested"
    set_act_environment_enabled(True)

    def inner() -> str:
        return "inner"

    def outer() -> str:
        assert act_call(inner) == "inner"
        return "outer"

    assert act_call(outer) == "outer"
