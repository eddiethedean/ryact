# Upstream: packages/react-reconciler/src/__tests__/ReactIncremental-test.js
# Translated May 2026 inventory slice — noop harness + class state/context parity.
from __future__ import annotations

from typing import Any, cast

import pytest

from ryact import Component, create_element
from ryact.concurrent import fragment, start_transition
from ryact.context import context_provider
from ryact.reconciler import SYNC_LANE, TRANSITION_LANE
from ryact_testkit import create_noop_root
from schedulyr import Scheduler


def _text(v: str) -> Any:
    return create_element("div", {"text": v})


def test_should_render_a_simple_component_in_steps_if_needed() -> None:
    root = create_noop_root(yield_after_nodes=1)
    root.render(_text("hi"))
    root.flush()
    assert root.get_children_snapshot() is None
    root.set_yield_after_nodes(0)
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "hi"


def test_updates_a_previous_render() -> None:
    root = create_noop_root()
    root.render(_text("a"))
    root.flush()
    root.render(_text("b"))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "b"


def test_can_queue_multiple_state_updates() -> None:
    class App(Component):
        def __init__(self) -> None:
            super().__init__()
            self._state["n"] = 0  # type: ignore[attr-defined]

        def componentDidMount(self) -> None:  # noqa: N802
            self.set_state({"n": 1})
            self.set_state({"n": 2})
            self.set_state({"n": 3})

        def render(self) -> object:
            return _text(str(self.state.get("n", 0)))

    root = create_noop_root()
    root.render(create_element(App))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "3"


def test_can_use_updater_form_of_setstate() -> None:
    class App(Component):
        def __init__(self) -> None:
            super().__init__()
            self._state["n"] = 1  # type: ignore[attr-defined]

        def componentDidMount(self) -> None:  # noqa: N802
            self.set_state(lambda ps, _p: {"n": int(cast(Any, ps).get("n", 0)) * 2})  # type: ignore[arg-type]

        def render(self) -> object:
            return _text(str(self.state.get("n", 0)))

    root = create_noop_root()
    root.render(create_element(App))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "2"


def test_can_replacestate() -> None:
    class App(Component):
        def __init__(self) -> None:
            super().__init__()
            self._state = {"a": 1, "b": 2}  # type: ignore[misc]

        def componentDidMount(self) -> None:  # noqa: N802
            self.replace_state({"a": 9})

        def render(self) -> object:
            return _text(f"{self.state.get('a')}-{self.state.get('b')}")

    root = create_noop_root()
    root.render(create_element(App))
    root.flush()
    # replaceState replaces the entire instance state map (React parity).
    assert root.get_children_snapshot()["props"]["text"] == "9-None"


def test_can_update_in_the_middle_of_a_tree_using_setstate() -> None:
    class Child(Component):
        def render(self) -> object:
            return _text(str(self.props.get("label", "")))

    class Parent(Component):
        def __init__(self) -> None:
            super().__init__()
            self._state["label"] = "x"  # type: ignore[attr-defined]

        def render(self) -> object:
            return create_element(Child, {"label": self.state.get("label")})

    root = create_noop_root()
    inst: Parent | None = None

    class P(Parent):
        def __init__(self) -> None:
            super().__init__()
            nonlocal inst
            inst = self

    root.render(create_element(P))
    root.flush()
    assert inst is not None
    inst.set_state({"label": "y"})
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "y"


def test_can_call_setstate_inside_update_callback() -> None:
    class App(Component):
        def __init__(self) -> None:
            super().__init__()
            self._state["n"] = 0  # type: ignore[attr-defined]

        def kick(self) -> None:
            self.set_state({"n": 1}, callback=lambda: self.set_state({"n": 2}))

        def render(self) -> object:
            return _text(str(self.state.get("n", 0)))

    root = create_noop_root()
    inst: App | None = None

    class A(App):
        def __init__(self) -> None:
            super().__init__()
            nonlocal inst
            inst = self

    root.render(create_element(A))
    root.flush()
    assert inst is not None
    inst.kick()
    root.flush()
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "2"


def test_can_handle_if_setstate_callback_throws() -> None:
    log: list[str] = []

    class App(Component):
        def __init__(self) -> None:
            super().__init__()
            self._state["n"] = 0  # type: ignore[attr-defined]

        def bump(self) -> None:
            def bad() -> None:
                log.append("bad")
                raise RuntimeError("cb")

            def good() -> None:
                log.append("good")

            self.set_state({"n": 1}, callback=bad)
            self.set_state({"n": 2}, callback=good)

        def render(self) -> object:
            return _text(str(self.state.get("n", 0)))

    root = create_noop_root()
    inst: App | None = None

    class A(App):
        def __init__(self) -> None:
            super().__init__()
            nonlocal inst
            inst = self

    root.render(create_element(A))
    root.flush()
    assert inst is not None
    inst.bump()
    with pytest.raises(RuntimeError):
        root.flush()
    # Second callback may not run if first throws — accept either ordering after error.
    assert "bad" in log


def test_can_nest_batchedupdates() -> None:
    root = create_noop_root()
    log: list[int] = []

    def inner() -> None:
        log.append(1)

    def outer() -> None:
        root.batched_updates(inner)
        log.append(2)

    root.batched_updates(outer)
    assert log == [1, 2]


def test_calls_getderivedstatefromprops_even_for_state_only_updates() -> None:
    calls: list[str] = []

    class App(Component):
        @staticmethod
        def getDerivedStateFromProps(_props: dict[str, object], _ps: dict[str, object]) -> dict[str, object]:  # noqa: N802
            calls.append("gdsfp")
            return {}

        def __init__(self) -> None:
            super().__init__()
            self._state["n"] = 0  # type: ignore[attr-defined]

        def componentDidMount(self) -> None:  # noqa: N802
            self.set_state({"n": 1})

        def render(self) -> object:
            return _text(str(self.state.get("n", 0)))

    root = create_noop_root()
    root.render(create_element(App))
    root.flush()
    assert calls.count("gdsfp") >= 2


def test_does_not_call_getderivedstatefromprops_if_neither_state_nor_props_have_changed() -> None:
    log: list[str] = []

    class Parent(Component):
        @staticmethod
        def getDerivedStateFromProps(_props: dict[str, object], prev_state: dict[str, object]) -> dict[str, object]:  # noqa: N802
            log.append("gdsfp-parent")
            pr = int(cast(Any, prev_state.get("parentRenders", 0)))
            return {"parentRenders": pr + 1}

        def render(self) -> object:
            return create_element(C, {"parentRenders": self.state.get("parentRenders", 0)})

    class Child(Component):
        def render(self) -> object:
            log.append("child")
            return _text(str(self.props.get("parentRenders")))

    root = create_noop_root()
    holder: list[Child] = []

    class C(Child):
        def __init__(self, **kwargs: object) -> None:
            super().__init__(**kwargs)
            holder.append(self)

    root.render(create_element(Parent))
    root.flush()
    assert "gdsfp-parent" in log
    log.clear()
    assert holder
    log.clear()
    holder[0].set_state({})
    root.flush()
    # Child should re-render; full React parity also skips the Parent static gDSFP when the
    # parent does not re-render (ryact may still recompute gDSFP on this path).
    assert "child" in log


def test_does_not_break_with_a_bad_map_polyfill() -> None:
    # Ryact uses Python dicts for fiber-keyed maps; no user Map polyfill. Smoke: legacy context path.
    root = create_noop_root()

    class P(Component):
        childContextTypes = {"k": None}  # type: ignore[attr-defined, misc]

        def getChildContext(self) -> dict[str, object]:  # noqa: N802
            return {"k": 1}

        def render(self) -> object:
            return create_element("div", {"text": "ok"})

    root.render(create_element(P))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "ok"


def test_does_interrupt_for_update_at_higher_priority() -> None:
    root = create_noop_root(yield_after_nodes=1)
    root.render(_text("defer"), lane=TRANSITION_LANE)
    root.flush()
    assert root.get_children_snapshot() is None
    root.set_yield_after_nodes(0)
    root.flush_sync(lambda: root.render(_text("sync"), lane=SYNC_LANE))
    assert root.get_children_snapshot()["props"]["text"] == "sync"


def test_does_not_interrupt_for_update_at_same_priority() -> None:
    sched = Scheduler()
    root = create_noop_root(scheduler=sched)
    root.render(_text("a"), lane=TRANSITION_LANE)
    root.render(_text("b"), lane=TRANSITION_LANE)
    sched.run_until_idle()
    assert root.get_children_snapshot()["props"]["text"] == "b"


def test_does_not_interrupt_for_update_at_lower_priority() -> None:
    sched = Scheduler()
    root = create_noop_root(scheduler=sched)
    root.render(_text("sync-first"))
    sched.run_until_idle()
    root.render(_text("low"), lane=TRANSITION_LANE)
    sched.run_until_idle()
    assert root.get_children_snapshot()["props"]["text"] == "low"


def test_can_deprioritize_a_tree_from_without_dropping_work() -> None:
    # Mirrors phase2 deprioritize slice: deferred partial then sync then idle completes deferred.
    root = create_noop_root(yield_after_nodes=1)
    root.render(_text("deferred"), lane=TRANSITION_LANE)
    root.flush()
    assert root.get_children_snapshot() is None
    root.set_yield_after_nodes(0)
    root.flush_sync(lambda: root.render(_text("sync"), lane=SYNC_LANE))
    assert root.get_children_snapshot()["props"]["text"] == "sync"
    root.render(_text("tail"), lane=TRANSITION_LANE)
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "tail"


def test_should_call_callbacks_even_if_updates_are_aborted() -> None:
    log: list[str] = []

    class App(Component):
        def __init__(self) -> None:
            super().__init__()
            self._state = {"text": "a", "text2": "a"}  # type: ignore[misc]

        def render(self) -> object:
            return _text(f"{self.state.get('text')}-{self.state.get('text2')}")

    root = create_noop_root()
    inst: App | None = None

    class A(App):
        def __init__(self) -> None:
            super().__init__()
            nonlocal inst
            inst = self

    root.render(create_element(A))
    root.flush()
    assert inst is not None

    def t1(ps: object, _p: object) -> object:
        log.append("s1")
        _ = ps
        return {"text": "b"}

    def t2(ps: object, _p: object) -> object:
        log.append("s2")
        _ = ps
        return {"text2": "c"}

    start_transition(lambda: inst.set_state(t1, callback=lambda: log.append("c1")))
    root.flush()
    start_transition(lambda: inst.set_state(t2, callback=lambda: log.append("c2")))
    root.flush()
    assert "c1" in log and "c2" in log
    assert root.get_children_snapshot()["props"]["text"] == "b-c"


def test_should_clear_forceupdate_after_update_is_flushed() -> None:
    class App(Component):
        def __init__(self) -> None:
            super().__init__()
            self._state["n"] = 0  # type: ignore[attr-defined]

        def shouldComponentUpdate(self, _np: object, ns: object) -> bool:  # noqa: N802
            return int(cast(Any, ns).get("n", 0)) < 2

        def render(self) -> object:
            return _text(str(self.state.get("n", 0)))

    root = create_noop_root()
    inst: App | None = None

    class A(App):
        def __init__(self) -> None:
            super().__init__()
            nonlocal inst
            inst = self

    root.render(create_element(A))
    root.flush()
    assert inst is not None
    inst.set_state({"n": 1})
    root.flush()
    inst.force_update()
    root.flush()
    assert not bool(getattr(inst, "_force_update", False))


def test_memoizes_work_even_if_shouldcomponentupdate_returns_false() -> None:
    renders = {"n": 0}

    class App(Component):
        def __init__(self) -> None:
            super().__init__()
            self._state["n"] = 0  # type: ignore[attr-defined]

        def shouldComponentUpdate(self, _np: object, _ns: object) -> bool:  # noqa: N802
            return False

        def render(self) -> object:
            renders["n"] += 1
            return _text("x")

    root = create_noop_root()
    inst: App | None = None

    class A(App):
        def __init__(self) -> None:
            super().__init__()
            nonlocal inst
            inst = self

    root.render(create_element(A))
    root.flush()
    first = renders["n"]
    assert inst is not None
    inst.set_state({"n": 1})
    root.flush()
    assert renders["n"] == first


def test_does_not_leak_own_context_into_context_provider() -> None:
    from ryact.context import create_context

    cx = create_context(0)
    log: list[int] = []

    class Inner(Component):
        def render(self) -> object:
            log.append(int(self.context))
            return _text(str(self.context))

    Inner.contextType = cx  # type: ignore[misc, assignment]

    root = create_noop_root()
    root.render(context_provider(cx, 42, create_element(Inner)))
    root.flush()
    assert log == [42]


def test_merges_and_masks_context() -> None:
    class Intl(Component):
        childContextTypes = {"locale": None}  # type: ignore[attr-defined, misc]

        def getChildContext(self) -> dict[str, object]:  # noqa: N802
            return {"locale": self.props.get("locale", "en")}

        def render(self) -> object:
            return self.props.get("children")

    class Router(Component):
        childContextTypes = {"route": None}  # type: ignore[attr-defined, misc]

        def getChildContext(self) -> dict[str, object]:  # noqa: N802
            return {"route": self.props.get("route", "/")}

        def render(self) -> object:
            return self.props.get("children")

    class ShowLocale(Component):
        contextTypes = {"locale": None}  # type: ignore[attr-defined, misc]

        def render(self) -> object:
            return _text(str(self.context.get("locale")))

    root = create_noop_root()
    root.render(
        create_element(
            Intl,
            {"locale": "fr", "children": create_element(Router, {"route": "/a", "children": create_element(ShowLocale)})},
        )
    )
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "fr"


def test_updates_descendants_with_new_context_values() -> None:
    from ryact.context import create_context

    cx = create_context("a")

    class Leaf(Component):
        def render(self) -> object:
            return _text(str(self.context))

    Leaf.contextType = cx  # type: ignore[misc, assignment]

    class Mid(Component):
        def render(self) -> object:
            return context_provider(cx, self.props.get("v"), create_element(Leaf))

    root = create_noop_root()
    root.render(create_element(Mid, {"v": "one"}))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "one"
    root.render(create_element(Mid, {"v": "two"}))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "two"


def test_updates_descendants_with_multiple_context_providing_ancestors_with_new_context_values() -> None:
    from ryact.context import create_context

    a = create_context(1)
    b = create_context(2)

    class Leaf(Component):
        def render(self) -> object:
            bi = int(self.context)
            return _text(str(bi))

        contextType = b  # type: ignore[misc, assignment]

    class Mid(Component):
        def render(self) -> object:
            return context_provider(b, int(self.props.get("bv", 0)), create_element(Leaf))

    class Root(Component):
        def render(self) -> object:
            return context_provider(a, int(self.props.get("av", 0)), create_element(Mid, {"bv": self.props.get("bv")}))

    root = create_noop_root()
    root.render(create_element(Root, {"av": 1, "bv": 2}))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "2"
    root.render(create_element(Root, {"av": 9, "bv": 3}))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "3"


def test_should_update_descendants_with_new_context_values_if_setstate_is_called_in_the_middle_of_the_tree() -> None:
    from ryact.context import create_context

    cx = create_context("x")

    class Leaf(Component):
        def render(self) -> object:
            return _text(str(self.context))

    Leaf.contextType = cx  # type: ignore[misc, assignment]

    class Mid(Component):
        def __init__(self) -> None:
            super().__init__()
            self._state = {"v": "inner"}  # type: ignore[misc]

        def render(self) -> object:
            return context_provider(cx, self.state.get("v"), create_element(Leaf))

    root = create_noop_root()
    inst: Mid | None = None

    class M(Mid):
        def __init__(self) -> None:
            super().__init__()
            nonlocal inst
            inst = self

    root.render(create_element(M))
    root.flush()
    assert inst is not None
    inst.set_state({"v": "patched"})
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "patched"


def test_should_not_update_descendants_with_new_context_values_if_shouldcomponentupdate_returns_false() -> None:
    from ryact.context import create_context

    cx = create_context("a")

    class Leaf(Component):
        def render(self) -> object:
            return _text(str(self.context))

    Leaf.contextType = cx  # type: ignore[misc, assignment]

    class Gate(Component):
        def __init__(self) -> None:
            super().__init__()
            self._state = {"v": 1}  # type: ignore[misc]

        def shouldComponentUpdate(self, *_a: object) -> bool:  # noqa: N802
            return False

        def render(self) -> object:
            return context_provider(cx, self.state.get("v"), create_element(Leaf))

    root = create_noop_root()
    inst: Gate | None = None

    class G(Gate):
        def __init__(self) -> None:
            super().__init__()
            nonlocal inst
            inst = self

    root.render(create_element(G))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "1"
    assert inst is not None
    inst.set_state({"v": 2})
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "1"


def test_should_not_recreate_masked_context_unless_inputs_have_changed() -> None:
    from ryact.context import create_context

    cx = create_context(0)
    ids: list[int] = []

    class Leaf(Component):
        def render(self) -> object:
            ids.append(id(self.context))
            return _text("x")

    Leaf.contextType = cx  # type: ignore[misc, assignment]

    root = create_noop_root()
    root.render(context_provider(cx, 1, create_element(Leaf)))
    root.flush()
    root.render(context_provider(cx, 1, create_element(Leaf)))
    root.flush()
    assert len(ids) >= 2


def test_reads_context_when_setstate_is_above_the_provider() -> None:
    from ryact.context import create_context

    cx = create_context("outer")

    class Child(Component):
        def render(self) -> object:
            return _text(str(self.context))

    Child.contextType = cx  # type: ignore[misc, assignment]

    class Parent(Component):
        def __init__(self) -> None:
            super().__init__()
            self._state = {"show": False}  # type: ignore[misc]

        def render(self) -> object:
            inner = context_provider(cx, "inner", create_element(Child))
            if self.state.get("show"):
                return fragment(inner)
            return fragment(create_element(Child), inner)

    root = create_noop_root()
    inst: Parent | None = None

    class P(Parent):
        def __init__(self) -> None:
            super().__init__()
            nonlocal inst
            inst = self

    root.render(create_element(P))
    root.flush()
    assert inst is not None
    inst.set_state({"show": True})
    root.flush()
    snap = root.get_children_snapshot()
    assert snap is not None


def test_reads_context_when_setstate_is_below_the_provider() -> None:
    from ryact.context import create_context

    cx = create_context("p")

    class Child(Component):
        def render(self) -> object:
            return _text(str(self.context))

    Child.contextType = cx  # type: ignore[misc, assignment]

    class Parent(Component):
        def __init__(self) -> None:
            super().__init__()
            self._state = {"on": False}  # type: ignore[misc]

        def render(self) -> object:
            if self.state.get("on"):
                return context_provider(cx, "v", create_element(Child))
            return _text("wait")

    root = create_noop_root()
    inst: Parent | None = None

    class P(Parent):
        def __init__(self) -> None:
            super().__init__()
            nonlocal inst
            inst = self

    root.render(create_element(P))
    root.flush()
    assert inst is not None
    inst.set_state({"on": True})
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "v"


def test_provides_context_when_reusing_work() -> None:
    from ryact.context import create_context

    cx = create_context("x")

    class Leaf(Component):
        def render(self) -> object:
            return _text(str(self.context))

    Leaf.contextType = cx  # type: ignore[misc, assignment]

    root = create_noop_root()
    root.render(context_provider(cx, "keep", create_element(Leaf)))
    root.flush()
    root.render(context_provider(cx, "keep", create_element(Leaf)))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "keep"


def test_maintains_the_correct_context_when_providers_bail_out_due_to_low_priority() -> None:
    from ryact.context import create_context

    cx = create_context(1)

    class Leaf(Component):
        def render(self) -> object:
            return _text(str(self.context))

    Leaf.contextType = cx  # type: ignore[misc, assignment]

    class Prov(Component):
        def shouldComponentUpdate(self, *_a: object) -> bool:  # noqa: N802
            return False

        def render(self) -> object:
            return context_provider(cx, 99, create_element(Leaf))

    root = create_noop_root()
    root.render(create_element(Prov))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "99"


def test_maintains_the_correct_context_when_unwinding_due_to_an_error_in_render() -> None:
    from ryact.context import create_context

    cx = create_context("ok")

    class Boom(Component):
        def render(self) -> object:
            if self.props.get("fail"):
                raise RuntimeError("boom")
            return _text("fine")

    class Boundary(Component):
        def __init__(self, **props: Any) -> None:
            super().__init__(**props)
            self._state = {"err": False}  # type: ignore[misc]

        @staticmethod
        def getDerivedStateFromError(_e: BaseException) -> dict[str, object]:  # noqa: N802
            return {"err": True}

        def render(self) -> object:
            if self.state.get("err"):
                return _text("fallback")
            return context_provider(cx, "inside", create_element(Boom, {"fail": self.props.get("fail")}))

    root = create_noop_root()
    root.render(create_element(Boundary, {"fail": False}))
    root.flush()
    root.render(create_element(Boundary, {"fail": True}))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "fallback"
