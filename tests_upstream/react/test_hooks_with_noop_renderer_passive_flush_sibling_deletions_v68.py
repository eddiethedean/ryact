from __future__ import annotations

from typing import Any

from ryact import create_element, fragment, use_effect, use_state
from ryact_testkit import act, create_noop_root, set_act_environment_enabled


def test_flushes_passive_effects_even_with_sibling_deletions() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "flushes passive effects even with sibling deletions"
    log: list[str] = []
    root = create_noop_root()
    api: dict[str, Any] = {}

    def A(*, show: bool, key: str | None = None) -> Any:
        _ = key

        def eff() -> Any:
            log.append(f"A:mount:{show}")

            def cleanup() -> None:
                log.append(f"A:unmount:{show}")

            return cleanup

        use_effect(eff, (show,))
        return create_element("span", {"text": "A"})

    def B(*, key: str | None = None) -> Any:
        _ = key

        def eff() -> Any:
            log.append("B:mount")

            def cleanup() -> None:
                log.append("B:unmount")

            return cleanup

        use_effect(eff, ())
        return create_element("span", {"text": "B"})

    def App() -> Any:
        show, set_show = use_state(True)
        api["toggle"] = lambda: set_show(False)
        children: list[Any] = [create_element(A, {"show": show, "key": "a"})]
        if show:
            children.append(create_element(B, {"key": "b"}))
        return fragment(*children)

    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App))

        assert "B:mount" in log

        with act(flush=root.flush):
            api["toggle"]()

        # When B is deleted, its passive cleanup should still flush, and A should
        # be able to flush its own effect update in the same commit cycle.
        assert "B:unmount" in log
        assert any(x.startswith("A:mount:False") for x in log)
    finally:
        set_act_environment_enabled(False)

