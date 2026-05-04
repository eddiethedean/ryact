from __future__ import annotations

from typing import Any

from ryact import create_element, fragment, use_effect
from ryact_testkit import act, create_noop_root, set_act_environment_enabled


def test_flushes_passive_effects_even_if_siblings_schedule_a_new_root() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "flushes passive effects even if siblings schedule a new root"
    log: list[str] = []

    other = create_noop_root()

    def OtherApp() -> Any:
        log.append("other:render")
        return create_element("span", {"text": "other"})

    def A(*, key: str | None = None) -> Any:
        _ = key

        def eff() -> Any:
            log.append("A:effect")
            # Schedule work on a different root during passive effect flush.
            other.render(create_element(OtherApp))
            return None

        use_effect(eff, ())
        return create_element("span", {"text": "A"})

    def B(*, key: str | None = None) -> Any:
        _ = key

        def eff() -> Any:
            log.append("B:effect")
            return None

        use_effect(eff, ())
        return create_element("span", {"text": "B"})

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(fragment(create_element(A, {"key": "a"}), create_element(B, {"key": "b"})))
    finally:
        set_act_environment_enabled(False)

    # Both passive effects should flush, even though one schedules work on another root.
    assert "A:effect" in log
    assert "B:effect" in log
    assert "other:render" in log

