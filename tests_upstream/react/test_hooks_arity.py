from __future__ import annotations

import inspect

from ryact.hooks import _render_with_hooks, use_reducer, use_state


def test_usestate_setter_arity_is_one() -> None:
    hooks: list[object] = []

    def component() -> object:
        _value, set_state = use_state(0)
        return set_state

    set_state = _render_with_hooks(component, {}, hooks)
    params = list(inspect.signature(set_state).parameters.values())
    assert len(params) == 1
    assert params[0].kind in (
        inspect.Parameter.POSITIONAL_ONLY,
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
    )


def test_usereducer_dispatch_arity_is_one() -> None:
    hooks: list[object] = []

    def reducer(state: int, action: int) -> int:
        return state + action

    def component() -> object:
        _value, dispatch = use_reducer(reducer, 0)
        return dispatch

    dispatch = _render_with_hooks(component, {}, hooks)
    params = list(inspect.signature(dispatch).parameters.values())
    assert len(params) == 1
    assert params[0].kind in (
        inspect.Parameter.POSITIONAL_ONLY,
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
    )
