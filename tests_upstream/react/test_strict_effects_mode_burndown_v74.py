from __future__ import annotations

from collections.abc import Callable

from ryact import StrictMode, create_element, use_effect
from ryact.dev import set_dev
from ryact_testkit import create_noop_root


def test_double_flushing_passive_effects_only_results_in_one_double_invoke() -> None:
    # Upstream: StrictEffectsMode-test.js
    #
    # In our noop host, passive effects run during the commit phase and StrictEffectsMode
    # replay happens once for newly mounted effects. A second flush with no pending updates
    # must not trigger additional replays.
    set_dev(True)
    try:
        log: list[str] = []
        root = create_noop_root()

        def App() -> object:
            def eff() -> Callable[[], None] | None:
                log.append("mount")

                def cleanup() -> None:
                    log.append("cleanup")

                return cleanup

            use_effect(eff, ())
            return create_element("div")

        root.render(create_element(StrictMode, None, create_element(App)))
        assert log == ["mount", "cleanup", "mount"]

        root.flush()
        assert log == ["mount", "cleanup", "mount"]
    finally:
        set_dev(False)
