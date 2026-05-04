from __future__ import annotations

from typing import Any, Callable

from ryact import create_element, memo, use_state

_Setter = Callable[[Any], None]
from ryact_testkit import act, create_noop_root, set_act_environment_enabled


def test_usestate_lazy_state_initializer() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "lazy state initializer"
    calls = 0

    def App() -> object:
        nonlocal calls

        def init() -> int:
            nonlocal calls
            calls += 1
            return 1

        v, _ = use_state(init)  # type: ignore[misc]
        return create_element("span", {"children": [str(v)]})

    set_act_environment_enabled(True)
    root = create_noop_root()
    try:
        with act(flush=root.flush):
            root.render(create_element(App, {}))
        with act(flush=root.flush):
            root.render(create_element(App, {}))
    finally:
        set_act_environment_enabled(False)
    assert calls == 1


def test_usestate_multiple_states() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "multiple states"
    def App() -> object:
        a, _ = use_state(1)
        b, _ = use_state(2)
        return create_element("span", {"children": [f"{a},{b}"]})

    root = create_noop_root()
    root.render(create_element(App, {}))
    assert "1,2" in str(root.get_children_snapshot())


def test_usestate_returns_same_updater_function_every_time() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "returns the same updater function every time"
    setters: list[_Setter] = []

    def App() -> object:
        _, set_v = use_state(0)
        setters.append(set_v)
        return create_element("span", {"children": ["ok"]})

    root = create_noop_root()
    root.render(create_element(App, {}))
    root.render(create_element(App, {}))
    assert setters[0] is setters[1]


def test_usestate_simple_mount_and_update() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "simple mount and update"
    set_act_environment_enabled(True)
    root = create_noop_root()

    set_v: list[_Setter | None] = [None]

    def App() -> object:
        v, s = use_state(0)
        set_v[0] = s
        return create_element("span", {"children": [str(v)]})

    try:
        with act(flush=root.flush):
            root.render(create_element(App, {}))
        assert "0" in str(root.get_children_snapshot())
        with act(flush=root.flush):
            sv = set_v[0]
            assert sv is not None
            sv(1)
    finally:
        set_act_environment_enabled(False)
    assert "1" in str(root.get_children_snapshot())


def test_usestate_works_with_memo() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "works with memo"
    renders: list[int] = []

    def Inner() -> object:
        v, set_v = use_state(0)
        renders.append(v)
        if v < 1:
            set_v(1)
        return create_element("span", {"children": [str(v)]})

    App = memo(Inner)

    set_act_environment_enabled(True)
    root = create_noop_root()
    try:
        with act(flush=root.flush):
            root.render(create_element(App, {}))
    finally:
        set_act_environment_enabled(False)
    assert renders and renders[-1] == 1
