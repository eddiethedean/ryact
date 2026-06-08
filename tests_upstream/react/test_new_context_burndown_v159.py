# Translated from: packages/react-reconciler/src/__tests__/ReactNewContext-test.js
# Burndown v159: provider bailout, consumer/readContext semantics.
from __future__ import annotations

from typing import Any, cast

from ryact import Component, create_element, create_ref, use_context
from ryact.context import context_provider, create_context
from ryact_testkit import create_noop_root


def _text(log: list[str], label: str) -> Any:
    log.append(label)
    return create_element("span", {"text": label})


def test_provider_bails_out_if_children_and_value_are_unchanged() -> None:
    log: list[str] = []
    Ctx = create_context(0)

    def Child() -> object:
        return _text(log, "Child")

    stable_child = create_element(Child)

    def App(*, value: int) -> object:
        log.append("App")
        return context_provider(Ctx, value, stable_child)

    root = create_noop_root()
    root.render(create_element(App, {"value": 1}))
    root.flush()
    assert log == ["App", "Child"]

    log.clear()
    root.render(create_element(App, {"value": 1}))
    root.flush()
    assert log == ["App"]


def test_can_read_other_contexts_inside_consumer_render_prop() -> None:
    FooCtx = create_context(0)
    BarCtx = create_context(0)
    log: list[str] = []

    def render_foo(foo: int) -> object:
        bar = BarCtx._get()
        log.append(f"Foo: {foo}, Bar: {bar}")
        return create_element("span", {"text": f"{foo},{bar}"})

    def App(*, foo: int, bar: int) -> object:
        return context_provider(
            FooCtx,
            foo,
            context_provider(
                BarCtx,
                bar,
                create_element(FooCtx.Consumer, None, render_foo),
            ),
        )

    root = create_noop_root()
    root.render(create_element(App, {"foo": 1, "bar": 1}))
    root.flush()
    assert log == ["Foo: 1, Bar: 1"]
    assert root.get_children_snapshot()["props"]["text"] == "1,1"

    log.clear()
    root.render(create_element(App, {"foo": 2, "bar": 1}))
    root.flush()
    assert log == ["Foo: 2, Bar: 1"]


def test_consumer_does_not_bail_out_if_there_were_no_bailouts_above_it() -> None:
    Ctx = create_context(0)
    log: list[str] = []
    inst_ref = create_ref()

    class App(Component):
        def __init__(self, **props: Any) -> None:
            super().__init__(**props)
            self._state["text"] = "hello"  # type: ignore[attr-defined]

        def render_consumer(self, _ctx: int) -> object:
            log.append("App#renderConsumer")
            return create_element("span", {"text": self.state["text"]})

        def render(self) -> object:
            log.append("App")
            return context_provider(
                Ctx,
                0,
                create_element(Ctx.Consumer, None, self.render_consumer),
            )

    root = create_noop_root()
    root.render(create_element(App, {"ref": inst_ref}))
    root.flush()
    assert log == ["App", "App#renderConsumer"]

    log.clear()
    cast(Any, inst_ref.current).set_state({"text": "goodbye"})
    root.flush()
    assert log == ["App", "App#renderConsumer"]


def test_can_read_the_same_context_multiple_times_in_the_same_function() -> None:
    Ctx = create_context({"foo": 0, "bar": 0})
    log: list[str] = []

    def Reader() -> object:
        a = use_context(Ctx)
        b = use_context(Ctx)
        log.append(f"{a['foo']},{a['bar']}|{b['foo']},{b['bar']}")
        return create_element("span", {"text": f"{a['foo']},{a['bar']}"})

    root = create_noop_root()
    root.render(context_provider(Ctx, {"foo": 1, "bar": 2}, create_element(Reader)))
    root.flush()
    assert log == ["1,2|1,2"]
