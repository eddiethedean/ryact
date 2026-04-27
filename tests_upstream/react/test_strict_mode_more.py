from __future__ import annotations

import pytest

from ryact import Component, StrictMode, create_element, use_memo, use_reducer, use_state
from ryact.dev import set_dev
from ryact_testkit import WarningCapture, create_noop_root


def test_double_invokes_usememo_functions() -> None:
    # Upstream: ReactStrictMode-test.js
    # "double invokes useMemo functions"
    set_dev(True)
    calls: list[str] = []
    root = create_noop_root()

    def App() -> object:
        def factory() -> str:
            calls.append("memo")
            return "v"

        _v = use_memo(factory, ())
        return create_element("div")

    root.render(create_element(StrictMode, None, create_element(App)))
    assert calls == ["memo", "memo"]


def test_double_invokes_usememo_functions_with_first_result() -> None:
    # Upstream: ReactStrictMode-test.js
    # "double invokes useMemo functions with first result"
    set_dev(True)
    calls: list[int] = []
    root = create_noop_root()

    def App() -> object:
        n = use_memo(lambda: (calls.append(len(calls)) or len(calls)), ())
        # React keeps the first result even though the factory is invoked twice.
        assert n == 1
        return create_element("div")

    root.render(create_element(StrictMode, None, create_element(App)))
    assert calls == [0, 1]


def test_double_invokes_usestate_and_usereducer_initializers_functions() -> None:
    # Upstream: ReactStrictMode-test.js
    # "double invokes useState and useReducer initializers functions"
    set_dev(True)
    calls: list[str] = []
    root = create_noop_root()

    def init_state() -> int:
        calls.append("state")
        return 1

    def init_reducer(arg: int) -> int:
        calls.append("reducer_init")
        return arg + 1

    def reducer(state: int, action: int) -> int:
        return state + action

    def App() -> object:
        s, _set_s = use_state(init_state)
        r, _dispatch = use_reducer(reducer, 1, init_reducer)
        assert s == 1
        assert r == 2
        return create_element("div")

    root.render(create_element(StrictMode, None, create_element(App)))
    assert calls == ["state", "state", "reducer_init", "reducer_init"]


def test_double_invokes_setstate_updater_functions() -> None:
    # Upstream: ReactStrictMode-test.js
    # "double invokes setState updater functions"
    set_dev(True)
    calls: list[str] = []
    root = create_noop_root()

    class App(Component):
        def render(self) -> object:
            if not calls:
                self.set_state(lambda _s, _p: (calls.append("updater") or {"n": 1}))
            return create_element("div")

    root.render(create_element(StrictMode, None, create_element(App)))
    root.flush()
    assert calls == ["updater", "updater"]


def test_should_appear_in_the_client_component_stack() -> None:
    # Upstream: ReactStrictMode-test.js
    # "should appear in the client component stack"
    set_dev(True)

    def Boom() -> object:
        raise RuntimeError("boom")

    root = create_noop_root()
    with pytest.raises(RuntimeError) as exc:
        root.render(create_element(StrictMode, None, create_element(Boom)))
    assert "Component stack:" in str(exc.value)
    assert "in StrictMode" in str(exc.value)


def test_should_warn_about_unsafe_legacy_lifecycle_methods_anywhere_in_a_strictmode_tree() -> None:
    # Upstream: ReactStrictMode-test.js
    # "should warn about unsafe legacy lifecycle methods anywhere in a StrictMode tree"
    set_dev(True)

    class Legacy(Component):
        def componentWillMount(self) -> None:  # noqa: N802
            return None

        def render(self) -> object:
            return create_element("div")

    with WarningCapture() as cap:
        create_noop_root().render(create_element(StrictMode, None, create_element(Legacy)))
    assert any("unsafe" in str(r.message).lower() and "componentwillmount" in str(r.message).lower() for r in cap.records)

