from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

import pytest
from ryact import create_element, h, js_subtree, py_subtree, use_state
from ryact_testkit import StubInteropRunner, create_noop_root


def test_python_root_can_render_js_leaf_via_stub_runner() -> None:
    runner = StubInteropRunner()

    def render_js(props: dict[str, object] | None, children: list[object]) -> object:
        label = "" if props is None else str(props.get("label", ""))
        return h("span", {"id": "js"}, label)

    runner.register_js(
        module_id="mod",
        export="default",
        fn=lambda p, c: render_js(cast(dict[str, object] | None, p), list(c)),
    )

    root = create_noop_root(interop_runner=runner)
    tree = h("div", None, js_subtree(module_id="mod", props={"label": "ok"}))
    root.render(tree)
    snap = root.get_children_snapshot()
    assert snap["children"][0]["props"]["id"] == "js"


def test_js_root_can_render_python_leaf_via_stub_runner() -> None:
    runner = StubInteropRunner()

    def render_py(props: dict[str, object] | None, children: list[object]) -> object:
        return h("em", {"id": "py"}, "py")

    runner.register_py(component_id="Comp", fn=lambda p, c: render_py(cast(dict[str, object] | None, p), list(c)))

    root = create_noop_root(interop_runner=runner)
    tree = h("div", None, py_subtree(component_id="Comp"))
    root.render(tree)
    snap = root.get_children_snapshot()
    assert snap["children"][0]["props"]["id"] == "py"


def test_marshaled_props_must_be_jsonish() -> None:
    runner = StubInteropRunner()
    runner.register_js(module_id="mod", export="default", fn=lambda p, c: h("span", None, "x"))
    root = create_noop_root(interop_runner=runner)

    def bad() -> None:
        pass

    with pytest.raises(TypeError):
        root.render(js_subtree(module_id="mod", props={"cb": bad}))


def test_updates_work_across_boundary_but_state_does_not_cross() -> None:
    runner = StubInteropRunner()
    sink: dict[str, object] = {}

    def render_js(props: dict[str, object] | None, children: list[object]) -> object:
        n_obj = 0 if props is None else props.get("n", 0)
        assert isinstance(n_obj, int)
        n = n_obj
        return h("span", {"id": "n"}, str(n))

    runner.register_js(
        module_id="mod",
        export="default",
        fn=lambda p, c: render_js(cast(dict[str, object] | None, p), list(c)),
    )

    def App() -> object:
        n, set_n = use_state(0)
        sink["set_n"] = set_n
        return h("div", None, js_subtree(module_id="mod", props={"n": n}))

    root = create_noop_root(interop_runner=runner)
    root.render(create_element(App, None))
    first = root.get_children_snapshot()

    set_n = cast(Callable[[Any], None], sink["set_n"])
    set_n(2)
    root.render(create_element(App, None))
    second = root.get_children_snapshot()

    assert first != second
