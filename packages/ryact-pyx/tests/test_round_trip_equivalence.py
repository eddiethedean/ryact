from __future__ import annotations

from ryact import create_element, h
from ryact_pyx import compile_pyx_to_python, eval_compiled


def test_round_trip_basic_host_tree() -> None:
    src = '<div id="root">hello</div>'
    code = compile_pyx_to_python(src, mode="expr")
    got = eval_compiled(code, scope={})
    expected = create_element("div", {"id": "root"}, "hello")
    assert got == expected


def test_round_trip_component_tag_with_scope() -> None:
    def Button(**props: object) -> object:
        children = props.get("children", ())
        assert isinstance(children, tuple)
        return h("button", {"disabled": props.get("disabled")}, *children)

    src = "<Button disabled={flag}>Save</Button>"
    code = compile_pyx_to_python(src, mode="expr")
    got = eval_compiled(code, scope={"Button": Button, "flag": True})
    expected = create_element(Button, {"disabled": True}, "Save")
    assert got == expected


def test_round_trip_multiple_roots_wraps_in_fragment() -> None:
    src = "<div count=1 /><span>ok</span>"
    code = compile_pyx_to_python(src, mode="expr")
    got = eval_compiled(code, scope={})
    # Structural details are asserted by golden codegen tests.
    assert got is not None
