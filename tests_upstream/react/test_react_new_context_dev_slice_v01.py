from __future__ import annotations

import pytest
from ryact import Component, create_context, create_element, use_context
from ryact.dev import set_dev
from ryact.hooks import HookError
from ryact_testkit import WarningCapture, act_call, create_noop_root, set_act_environment_enabled


def test_context_provider_is_context_object() -> None:
    ctx = create_context({"value": "bar-initial"})
    assert ctx.Provider is ctx


def test_warns_if_no_value_prop_on_context_provider() -> None:
    ctx = create_context(None)
    set_dev(True)
    with WarningCapture() as cap:
        root = create_noop_root()
        act_call(
            lambda: root.render(
                create_element(
                    "__context_provider__",
                    {"context": ctx, "children": (), "not_value": "x"},
                )
            ),
            flush=root.flush,
        )
    assert any("value` prop is required" in str(r.message) for r in cap.records)


def test_warns_if_consumer_child_is_not_a_function() -> None:
    ctx = create_context(0)
    set_dev(True)
    with WarningCapture() as cap:
        root = create_noop_root()
        with pytest.raises(TypeError, match="is not a function"):
            act_call(
                lambda: root.render(create_element(ctx.Consumer, {"children": ()})),
                flush=root.flush,
            )
    assert any("context consumer" in str(r.message).lower() for r in cap.records)


def test_use_context_throws_inside_class_render() -> None:
    cx = create_context(0)

    class Foo(Component):
        def render(self) -> object:
            return create_element("span", None, str(use_context(cx)))

    set_dev(True)
    set_act_environment_enabled(True)
    root = create_noop_root()
    with pytest.raises(HookError, match="Invalid hook call"):
        act_call(lambda: root.render(create_element(Foo)), flush=root.flush)


def test_use_context_warns_when_passed_consumer() -> None:
    cx = create_context(0)

    def Foo() -> object:
        _ = use_context(cx.Consumer)
        return create_element("span")

    set_dev(True)
    set_act_environment_enabled(True)
    root = create_noop_root()
    with WarningCapture() as cap:
        act_call(lambda: root.render(create_element(Foo)), flush=root.flush)
    assert any("useContext(Context.Consumer)" in str(r.message) for r in cap.records)
