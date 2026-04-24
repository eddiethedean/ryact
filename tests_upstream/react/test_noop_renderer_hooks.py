from __future__ import annotations

from collections.abc import Callable

import pytest
from ryact import create_element
from ryact.hooks import HookError, use_effect, use_state
from ryact_testkit import create_noop_root


def test_hooks_throw_outside_render_phase() -> None:
    with pytest.raises(HookError):
        use_state(0)


def test_useeffect_always_fires_without_deps() -> None:
    log: list[str] = []

    def App() -> None:
        _v, set_v = use_state(0)

        def eff() -> Callable[[], None] | None:
            log.append("effect")

            def cleanup() -> None:
                log.append("cleanup")

            return cleanup

        use_effect(eff)
        # Trigger an update for the next render.
        set_v(1)
        return None

    root = create_noop_root()
    root.render(create_element(App))
    # After first commit: effect should have fired.
    assert log == ["effect"]

    root.render(create_element(App))
    # On second commit: cleanup then effect again.
    assert log == ["effect", "cleanup", "effect"]
