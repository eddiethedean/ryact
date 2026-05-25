"""ReactDOMOption-test.js parity: option children flattening and value (v135)."""

from __future__ import annotations

import warnings
from collections.abc import Iterator
import pytest
from ryact import create_element, use_state
from ryact.dev import is_dev
from ryact_dom.dom import Container, ElementNode
from ryact_dom.html_props import reset_dom_warning_state
from ryact_dom.root import create_root, hydrate_root
from ryact_dom.server import render_to_string
from ryact_dom.validate_dom_nesting import reset_validate_dom_nesting_dev_state


@pytest.fixture(autouse=True)
def _reset_dev_state() -> Iterator[None]:
    reset_dom_warning_state()
    reset_validate_dom_nesting_dev_state()
    yield


def _host(c: Container) -> ElementNode:
    h = c.root.children[0]
    assert isinstance(h, ElementNode)
    return h


def _option_text(host: ElementNode) -> str:
    assert host.tag.lower() == "option"
    return host.innerHTML


def test_should_flatten_children_to_a_string_4ac04d3d() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("option", None, 1, " ", "foo"))
    assert _option_text(_host(c)) == "1 foo"


def test_should_warn_for_invalid_child_tags_4a1c701a() -> None:
    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("option", None, 1, create_element("div", None, 2)))
    assert _option_text(_host(c)) == "1 2"
    assert any("cannot be a child of <option>" in str(w.message) for w in rec)


def test_should_warn_for_component_child_if_no_value_prop_bfe34840() -> None:
    def Foo() -> object:
        return "2"

    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("option", None, 1, create_element(Foo, None), 3))
    assert _option_text(_host(c)) == "1 2 3"
    assert any("Cannot infer the option value" in str(w.message) for w in rec)


def test_should_not_warn_for_component_child_if_value_prop_b733cdb9() -> None:
    def Foo() -> object:
        return "2"

    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("option", {"value": "x"}, 1, create_element(Foo, None), 3))
    assert _option_text(_host(c)) == "1 2 3"
    assert not any("Cannot infer the option value" in str(w.message) for w in rec)


def test_should_ignore_null_undefined_false_children_7378a728() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("option", None, 1, False, True, None, 2))
    assert _option_text(_host(c)) == "1 2"


def test_should_throw_on_object_children_14a77222() -> None:
    c = Container()
    r = create_root(c)
    with pytest.raises(TypeError):
        r.render(create_element("option", None, {}))
    with pytest.raises(TypeError):
        r.render(create_element("option", None, [{}]))
    with pytest.raises(TypeError):
        r.render(create_element("option", None, create_element("span", None, {})))


def test_should_support_element_ish_child_5fe50838() -> None:
    class Elementish:
        props: dict[str, str] = {"content": "hello"}

        def __str__(self) -> str:
            return self.props["content"]

    c = Container()
    r = create_root(c)
    r.render(create_element("option", None, Elementish()))
    assert _option_text(_host(c)) == "hello"
    assert _host(c).value == "hello"

    r.render(create_element("option", {"value": "hello"}, Elementish()))
    assert _host(c).value == "hello"

    r.render(create_element("option", None, 1, Elementish(), 2))
    assert _option_text(_host(c)) == "1 hello 2"
    assert _host(c).value == "hello"


def test_should_support_bigint_values_1216c098() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("option", {"value": 5}, 5))
    host = _host(c)
    assert _option_text(host) == "5"
    assert host.value == "5"


def test_should_be_able_to_use_dangerouslysetinnerhtml_6f30e33b() -> None:
    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("option", {"dangerouslySetInnerHTML": {"__html": "foobar"}}))
    assert _option_text(_host(c)) == "foobar"
    if is_dev():
        assert any("dangerouslyInnerHTML" in str(w.message) for w in rec)


def test_should_set_attribute_for_empty_value_b723e584() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("option", {"value": ""}))
    host = _host(c)
    assert host.has_attribute("value")
    assert host.get_attribute("value") == ""
    r.render(create_element("option", {"value": "lava"}))
    host = _host(c)
    assert host.get_attribute("value") == "lava"


def test_should_allow_ignoring_value_on_option_3007fad1() -> None:
    c = Container()
    r = create_root(c)

    def App() -> object:
        cur, set_cur = use_state(1)

        def _opts() -> tuple[object, ...]:
            return (
                create_element("option", None, "monkey"),
                create_element("option", {"selected": cur == 1}, "giraffe"),
                create_element("option", None, "gorilla"),
            )

        return create_element("select", None, *_opts())

    r.render(create_element(App, None))
    sel = _host(c)
    assert sel.selectedIndex == 1
    r.render(
        create_element(
            "select",
            None,
            create_element("option", None, "monkey"),
            create_element("option", None, "giraffe"),
            create_element("option", {"selected": True}, "gorilla"),
        )
    )
    assert _host(c).selectedIndex == 2


@pytest.mark.skipif(not is_dev(), reason="hydration nesting DEV warnings")
def test_generates_hydration_error_invalid_nested_tag_9958970c() -> None:
    c = Container()
    tree = create_element(
        "select",
        None,
        create_element(
            "option",
            None,
            create_element("div", None, "Bar"),
            "Foo",
            create_element("span", None, "Baz"),
        ),
    )
    html = render_to_string(tree)
    c.root.children.clear()
    outer = ElementNode(tag="div")
    outer._inner_html_preserved = html
    c.root.append_child(outer)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        hydrate_root(c, tree)
    assert any("cannot be a child of <option>" in str(w.message) for w in rec)
    opts = [ch for ch in c.root.children[0].children if isinstance(ch, ElementNode)]
    opt = next(ch for ch in opts if ch.tag.lower() == "option")
    assert "Bar" in opt.innerHTML and "Foo" in opt.innerHTML and "Baz" in opt.innerHTML


def test_should_warn_for_component_child_at_stack_bfe34840_dev() -> None:
    if not is_dev():
        pytest.skip("DEV-only")
    def Foo() -> object:
        return "2"

    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("option", None, create_element(Foo, None)))
    assert any("(at **)" in str(w.message) for w in rec)
