from __future__ import annotations

from typing import Any, Callable

from ryact import create_element, use_imperative_handle, use_ref, use_state
from ryact.hooks import RefObject
from ryact_testkit import act, create_noop_root, set_act_environment_enabled


def test_useimperativehandle_automatically_updates_when_deps_not_specified() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "automatically updates when deps are not specified"
    root = create_noop_root()
    set_tick: list[Callable[[Any], None] | None] = [None]
    latest_ref: list[RefObject | None] = [None]

    def App() -> Any:
        tick, set_t = use_state(0)
        set_tick[0] = set_t
        ref = use_ref(None)
        latest_ref[0] = ref
        use_imperative_handle(ref, lambda: tick)  # deps omitted -> update every render
        return create_element("div", {"text": "ok"})

    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App))
        assert latest_ref[0] is not None and latest_ref[0]["current"] == 0
        with act(flush=root.flush):
            st = set_tick[0]
            assert st is not None
            st(1)
        assert latest_ref[0] is not None and latest_ref[0]["current"] == 1
    finally:
        set_act_environment_enabled(False)


def test_useimperativehandle_does_not_update_when_deps_same() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "does not update when deps are the same"
    root = create_noop_root()
    set_tick: list[Callable[[Any], None] | None] = [None]
    latest_ref: list[RefObject | None] = [None]

    def App() -> Any:
        tick, set_t = use_state(0)
        set_tick[0] = set_t
        ref = use_ref(None)
        latest_ref[0] = ref
        # Deps constant -> handle should not change across updates.
        use_imperative_handle(ref, lambda: tick, (1,))
        return create_element("div", {"text": "ok"})

    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App))
        assert latest_ref[0] is not None and latest_ref[0]["current"] == 0
        with act(flush=root.flush):
            st = set_tick[0]
            assert st is not None
            st(1)
        # Handle should still reflect the original tick (deps unchanged -> effect not re-fired).
        assert latest_ref[0] is not None and latest_ref[0]["current"] == 0
    finally:
        set_act_environment_enabled(False)


def test_useimperativehandle_updates_when_deps_different() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "updates when deps are different"
    root = create_noop_root()
    set_tick: list[Callable[[Any], None] | None] = [None]
    latest_ref: list[RefObject | None] = [None]

    def App() -> Any:
        tick, set_t = use_state(0)
        set_tick[0] = set_t
        ref = use_ref(None)
        latest_ref[0] = ref
        use_imperative_handle(ref, lambda: tick, (tick,))
        return create_element("div", {"text": "ok"})

    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App))
        assert latest_ref[0] is not None and latest_ref[0]["current"] == 0
        with act(flush=root.flush):
            st = set_tick[0]
            assert st is not None
            st(1)
        assert latest_ref[0] is not None and latest_ref[0]["current"] == 1
    finally:
        set_act_environment_enabled(False)
