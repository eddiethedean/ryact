from __future__ import annotations

import pytest
from ryact import create_element
from ryact.hooks import HookError, use_state
from ryact_testkit import create_noop_root


def test_render_phase_updates_restart_until_stable() -> None:
    log: list[int] = []

    def App() -> None:
        v, set_v = use_state(0)
        log.append(v)
        if v < 3:
            set_v(v + 1)
        return None

    root = create_noop_root()
    root.render(create_element(App))
    # First commit should observe the final stabilized value and only commit once.
    assert log == [0, 1, 2, 3]


def test_render_phase_update_infinite_loop_throws() -> None:
    def App() -> None:
        v, set_v = use_state(0)
        set_v(v + 1)
        return None

    root = create_noop_root()
    root.container.uncaught_error_reporter = lambda _err: None  # type: ignore[attr-defined]
    with pytest.raises(HookError, match="Too many re-renders"):
        root.render(create_element(App))

