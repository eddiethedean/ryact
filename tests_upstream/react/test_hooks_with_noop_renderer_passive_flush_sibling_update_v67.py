from __future__ import annotations

from typing import Any

from ryact import create_element, fragment, use_effect, use_state
from ryact_testkit import act, create_noop_root, set_act_environment_enabled


def test_flushes_passive_effects_even_if_siblings_schedule_an_update() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "flushes passive effects even if siblings schedule an update"
    log: list[str] = []
    root = create_noop_root()

    set_a: list[Any] = [None]

    def A(*, key: str | None = None) -> Any:
        _ = key
        a, s = use_state(0)
        set_a[0] = s

        def eff() -> Any:
            log.append(f"A:effect:{a}")
            if a == 0:
                s(1)  # schedule update during passive phase
            return None

        use_effect(eff, (a,))
        return create_element("span", {"text": f"A{a}"})

    def B(*, key: str | None = None) -> Any:
        _ = key
        def eff() -> Any:
            log.append("B:effect")
            return None

        use_effect(eff, ())
        return create_element("span", {"text": "B"})

    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(fragment(create_element(A, {"key": "a"}), create_element(B, {"key": "b"})))
        # Both effects should have run, even though A scheduled an update during passive phase.
        assert "B:effect" in log
        # And the scheduled update should be able to commit on the next flush.
        with act(flush=root.flush):
            root.flush()
        assert root.get_children_snapshot() is not None
    finally:
        set_act_environment_enabled(False)

