from __future__ import annotations

from pathlib import Path

from ryact import create_element, js_subtree, py_subtree
from ryact_dom.dom import Container, ElementNode
from ryact_dom.interop_runner import DomInteropRunner
from ryact_dom.root import create_root


def test_dom_interop_runner_renders_js_boundary() -> None:
    # Minimal JS boundary execution: module_id -> python module with render(scope).
    container = Container()
    runner = DomInteropRunner()
    runner.register_module(
        module_id="m",
        path=Path(__file__).parent / "fixtures" / "dom_interop_js_module.py",
    )
    container.interop_runner = runner
    root = create_root(container)

    root.render(js_subtree(module_id="m", export="default", props={"id": "x"}, children=()))
    # Host root has one child element with id "x".
    host = container.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.tag == "div"
    assert host.props.get("id") == "x"


def test_dom_interop_runner_renders_py_boundary() -> None:
    container = Container()
    runner = DomInteropRunner()

    def Button(props, children):  # type: ignore[no-untyped-def]
        _ = children
        return create_element("button", {"id": props.get("id") if props else None})

    runner.register_py(component_id="Button", fn=Button)
    container.interop_runner = runner
    root = create_root(container)

    root.render(py_subtree(component_id="Button", props={"id": "b"}, children=()))
    host = container.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.tag == "button"
    assert host.props.get("id") == "b"
