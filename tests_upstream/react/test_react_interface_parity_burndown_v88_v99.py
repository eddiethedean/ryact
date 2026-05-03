# React ``packages/react`` interface parity (burndown v88–v99 synthetic slices).
from __future__ import annotations

from typing import Any

import pytest

import ryact as ryact_pkg

from ryact import (
    Activity,
    ContextConsumerMarker,
    FormStatusSnapshot,
    Offscreen,
    activity,
    clone_element,
    context_provider,
    create_context,
    create_element,
    create_ref,
    form_status_provider,
    is_valid_element,
    offscreen,
    use,
    use_action_state,
    use_context,
    use_debug_value,
    use_form_status,
    use_imperative_handle,
    version,
)
from ryact.concurrent import Thenable, is_in_transition, lazy, start_transition, suspense
from ryact.devtools import inspect_fiber_tree
from ryact.element import Element
from ryact_testkit import create_noop_root


def test_v88_is_valid_element_and_version() -> None:
    assert is_valid_element(create_element("div", None)) is True
    assert is_valid_element(Element(type="span", props={})) is True
    assert is_valid_element({"type": "fake"}) is False
    assert version == ryact_pkg.__version__


def test_v88_act_reexported_from_ryact() -> None:
    from ryact import act_call as ry_act_call

    assert ry_act_call(lambda: 42) == 42


def test_v89_use_context_reads_provider() -> None:
    root = create_noop_root()
    Ctx = create_context("default")

    def Reader() -> Any:
        return create_element("span", {"t": use_context(Ctx)})

    root.render(context_provider(Ctx, "provided", create_element(Reader)))
    root.flush()
    assert root.get_children_snapshot()["props"]["t"] == "provided"


def test_v90_use_imperative_handle_sets_ref() -> None:
    root = create_noop_root()
    r = create_ref()

    def Inner(**props: Any) -> Any:
        use_imperative_handle(props["iref"], lambda: {"mark": 99}, ())
        return create_element("span", {"ok": True})

    root.render(create_element(Inner, {"iref": r}))
    root.flush()
    assert r.current == {"mark": 99}


def test_v91_use_debug_value_surfaces_in_inspect_tree() -> None:
    root = create_noop_root()

    def App() -> Any:
        use_debug_value("x", lambda v: f"dbg:{v}")
        return create_element("span", {"a": 1})

    root.render(create_element(App))
    root.flush()

    def collect_labels(node: Any) -> list[str]:
        out: list[str] = []
        if node.debug_values:
            out.extend(node.debug_values)
        for ch in node.children:
            out.extend(collect_labels(ch))
        return out

    tree = inspect_fiber_tree(root._reconciler_root)
    assert tree is not None
    labels = collect_labels(tree)
    assert any("dbg:x" in lab for lab in labels)


def test_v92_use_action_state_initial_and_dispatch() -> None:
    root = create_noop_root()
    holder: dict[str, Any] = {}

    def App() -> Any:
        st, dispatch, pend = use_action_state(lambda prev, pl: prev + int(pl or 0), 10)
        holder["dispatch"] = dispatch
        return create_element("span", {"st": st, "pend": pend})

    root.render(create_element(App))
    root.flush()
    snap = root.get_children_snapshot()
    assert snap["props"]["st"] == 10
    holder["dispatch"](3)
    root.flush()
    snap2 = root.get_children_snapshot()
    assert snap2["props"]["st"] == 13


def test_v93_use_form_status_via_provider() -> None:
    root = create_noop_root()

    def Row() -> Any:
        fs = use_form_status()
        return create_element("span", {"pend": fs.pending})

    root.render(
        form_status_provider(
            FormStatusSnapshot(pending=True, data={"k": "v"}, method="post", action="/a"),
            create_element(Row),
        )
    )
    root.flush()
    assert root.get_children_snapshot()["props"]["pend"] is True


def test_v94_ref_as_prop_on_function_component() -> None:
    root = create_noop_root()

    def Fn(**props: Any) -> Any:
        return create_element("span", {"has_ref": props.get("ref") is not None})

    rr = create_ref()
    root.render(create_element(Fn, {"ref": rr}))
    root.flush()
    assert root.get_children_snapshot()["props"]["has_ref"] is True


def test_v95_activity_offscreen_exports() -> None:
    assert Activity is Offscreen
    el = activity(children=create_element("span", None), mode="hidden")
    assert isinstance(el, Element)
    assert el.type == Offscreen
    el2 = offscreen(children=create_element("div", None))
    assert el2.type == Offscreen


def test_v96_use_reads_context() -> None:
    root = create_noop_root()
    Ctx = create_context(42)

    def Reader() -> Any:
        return create_element("span", {"n": use(Ctx)})

    root.render(context_provider(Ctx, 99, create_element(Reader)))
    root.flush()
    assert root.get_children_snapshot()["props"]["n"] == 99


def test_v96_use_thenable_fulfilled() -> None:
    root = create_noop_root()
    t = Thenable()
    t.resolve("done")

    def App() -> Any:
        return create_element("span", {"v": use(t)})

    root.render(create_element(App))
    root.flush()
    assert root.get_children_snapshot()["props"]["v"] == "done"


def test_v97_lazy_inside_suspense_resolves() -> None:
    root = create_noop_root()
    t: Thenable = Thenable()

    def Inner() -> Any:
        return create_element("span", {"text": "loaded"})

    def loader() -> Any:
        return t

    LazyInner = lazy(loader)
    root.render(
        suspense(
            fallback=create_element("span", {"text": "wait"}),
            children=create_element(LazyInner),
        )
    )
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "wait"
    t.resolve({"default": Inner})
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "loaded"


def test_v98_nested_start_transition_sees_flag() -> None:
    observed: list[bool] = []

    def inner() -> None:
        observed.append(is_in_transition())

    def outer() -> None:
        start_transition(inner)

    start_transition(outer)
    assert observed == [True]


def test_v99_context_consumer_render_prop() -> None:
    root = create_noop_root()
    Ctx = create_context(0)
    Cons = Ctx.Consumer
    assert isinstance(Cons, ContextConsumerMarker)
    tree = create_element(
        Cons,
        {"children": (lambda v: create_element("span", {"v": v}),)},
    )
    root.render(context_provider(Ctx, 5, tree))
    root.flush()
    assert root.get_children_snapshot()["props"]["v"] == 5


def test_clone_preserves_is_valid_element() -> None:
    el = create_element("div", {"className": "a"}, "hi")
    c = clone_element(el, {"id": "z"})
    assert is_valid_element(c)
