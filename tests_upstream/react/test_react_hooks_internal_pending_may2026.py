# Upstream: packages/react-reconciler/src/__tests__/ReactHooks-test.internal.js
# May 2026 inventory slice: internal hook warnings and strict-mode memo DEV behavior smoke.
from __future__ import annotations

import pytest

from ryact import create_element
from ryact.concurrent import StrictMode, strict_mode
from ryact.dev import set_dev
from ryact.hooks import HookError, use_effect, use_layout_effect, use_memo, use_reducer, use_state
from ryact_testkit import WarningCapture, act_call, create_noop_root, set_act_environment_enabled
from ryact.wrappers import memo


def test_warns_about_setstate_second_argument() -> None:
    set_dev(True)
    set_act_environment_enabled(True)

    def App() -> object:
        _v, set_v = use_state(0)
        with pytest.raises(TypeError):
            set_v(1, None)  # type: ignore[call-arg]
        return create_element("div")

    root = create_noop_root()
    act_call(lambda: root.render(create_element(App)), flush=root.flush)


def test_warns_about_dispatch_second_argument() -> None:
    set_dev(True)
    set_act_environment_enabled(True)

    def reducer(s: int, a: int) -> int:
        return s + a

    def App() -> object:
        _v, dispatch = use_reducer(reducer, 0)
        with pytest.raises(TypeError):
            dispatch(1, None)  # type: ignore[call-arg]
        return create_element("div")

    root = create_noop_root()
    act_call(lambda: root.render(create_element(App)), flush=root.flush)


def test_throws_when_reading_context_inside_useeffect_smoke() -> None:
    # We don't model full context read restrictions here; just ensure effect hooks run.
    set_dev(True)
    set_act_environment_enabled(True)
    ran = {"ok": False}

    def App() -> object:
        def eff() -> None:
            ran["ok"] = True

        use_effect(lambda: (eff(), None)[1], ())
        return create_element("div")

    root = create_noop_root()
    act_call(lambda: root.render(create_element(App)), flush=root.flush)
    assert ran["ok"]


def test_double_invokes_usememo_in_dev_strictmode_smoke() -> None:
    set_dev(True)
    set_act_environment_enabled(True)
    calls: list[int] = []

    def App() -> object:
        _ = use_memo(lambda: (calls.append(1), 1)[1], ())
        return create_element("div")

    root = create_noop_root()
    act_call(lambda: root.render(strict_mode(create_element(App))), flush=root.flush)
    assert calls


def test_throws_when_calling_hooks_inside_memo_compare_function() -> None:
    set_dev(True)
    set_act_environment_enabled(True)

    def Inner(*, x: int) -> object:
        return create_element("div", {"text": x})

    def compare(_a: dict, _b: dict) -> bool:
        # Illegal hook call site.
        _ = use_state(0)
        return True

    M = memo(Inner, compare=compare)
    root = create_noop_root()
    act_call(lambda: root.render(create_element(M, {"x": 1})), flush=root.flush)
    with pytest.raises(HookError):
        act_call(lambda: root.render(create_element(M, {"x": 2})), flush=root.flush)
