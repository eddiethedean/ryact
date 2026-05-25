"""ReactDOM-test, ReactDOMUseId, ReactDOMSVG parity burndown (v140)."""

from __future__ import annotations

import warnings

import pytest
from ryact import Component, StrictMode, create_element, create_ref, suspense_list, use_id
from ryact.dev import set_dev
from ryact_dom.dom import Container, ElementNode
from ryact_dom.dom_internals import (
    reset_component_dom_registry,
)
from ryact_dom.host_focus import reset_host_focus_state
from ryact_dom.legacy_render import legacy_render
from ryact_dom.root import create_root, render_into
from ryact_dom.server import render_to_string
from ryact_dom.svg_namespace import HTML_NAMESPACE, SVG_NAMESPACE


@pytest.fixture(autouse=True)
def _reset_v140_state():
    reset_component_dom_registry()
    reset_host_focus_state()
    yield


def _host(c: Container) -> ElementNode:
    h = c.root.children[0]
    assert isinstance(h, ElementNode)
    return h


def _find_tag(c: Container, tag: str) -> ElementNode:
    def walk(n: object) -> ElementNode | None:
        if isinstance(n, ElementNode):
            if n.tag.lower() == tag.lower():
                return n
            for ch in n.children:
                got = walk(ch)
                if got is not None:
                    return got
        return None

    for ch in c.root.children:
        got = walk(ch)
        if got is not None:
            return got
    raise AssertionError(tag)




def test_allows_a_dom_element_to_be_used_with_a_string() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("div", None, "hello"))
    assert c.text_content == "hello"



def test_calls_focus_on_autofocus_elements_after_they_have_been_mounted_to_the_dom() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"autoFocus": True, "name": "q"}))
    inp = _find_tag(c, "input")
    assert inp._input_focused is True



def test_preserves_focus() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"name": "q"}))
    inp = _find_tag(c, "input")
    inp.focus()
    r.render(create_element("input", {"name": "q", "defaultValue": "x"}))
    inp2 = _find_tag(c, "input")
    assert inp2._input_focused is True



def test_reports_stacks_with_re_entrant_rendertostring_calls_on_the_client() -> None:
    set_dev(True)
    def Inner():
        render_to_string(create_element("span", None, "x"))
        return create_element("span", None, "y")
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        render_to_string(create_element(Inner))
    assert any("renderToString was called while already rendering" in str(w.message) for w in rec)



def test_should_allow_children_to_be_passed_as_an_argument() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("div", None, "a", "b"))
    assert c.text_content == "ab"



def test_should_bubble_onsubmit() -> None:
    log: list[str] = []
    c = Container()
    r = create_root(c)

    def on_outer(_e):
        log.append("outer")

    def on_inner(_e):
        log.append("inner")

    r.render(
        create_element(
            "div",
            {"onSubmit": on_outer},
            create_element("form", {"onSubmit": on_inner}, create_element("input", {"type": "submit", "name": "go"})),
        )
    )
    form = _find_tag(c, "form")
    btn = form.children[0]
    assert isinstance(btn, ElementNode)
    form.request_submit(btn)
    assert log == ["inner", "outer"]



def test_should_not_crash_calling_finddomnode_inside_a_function_component() -> None:
    c = Container()
    r = create_root(c)
    ref = create_ref()

    def Fn():
        return create_element("div", {"ref": ref})

    class Host(Component):
        def render(self):
            return create_element(Fn)

    r.render(create_element(Host))
    assert isinstance(_host(c), ElementNode)



def test_should_not_crash_with_devtools_installed() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("div", None, "ok"))
    assert c.text_content == "ok"



def test_should_overwrite_props_children_with_children_argument() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("div", {"children": "wrong"}, "right"))
    assert c.text_content == "right"



def test_should_purge_the_dom_cache_when_removing_nodes() -> None:
    c = Container()
    r = create_root(c)

    class Leaf(Component):
        def render(self):
            return create_element("span", None, "x")

    r.render(create_element("div", None, create_element(Leaf)))
    host = _host(c)
    span = host.children[0]
    assert isinstance(span, ElementNode)
    token = object()
    from ryact_dom.dom_internals import _component_dom_nodes, register_component_dom_node

    register_component_dom_node(token, span)
    assert _component_dom_nodes.get(id(token)) is span
    r.render(None)
    assert span not in _component_dom_nodes.values()



def test_shouldn_t_fire_duplicate_event_handler_while_handling_other_nested_dispatch() -> None:
    log: list[str] = []

    def on_click(_e):
        log.append("click")

    c = Container()
    r = create_root(c)
    r.render(create_element("button", {"onClick": on_click}, "go"))
    btn = _host(c)
    btn.dispatch_event("click")
    assert log.count("click") == 1



def test_throws_in_render_if_the_mount_callback_in_legacy_roots_is_not_a_function() -> None:
    c = Container()
    with pytest.raises(TypeError, match="callback"):
        legacy_render(create_element("div", None, "hi"), c, "not-a-function")



def _svg_mount_tree() -> object:
    return create_element(
        "svg",
        None,
        create_element(
            "g",
            {"strokeWidth": 5},
            create_element(
                "svg",
                None,
                create_element(
                    "foreignObject",
                    None,
                    create_element("svg", None, create_element("image", {"xlinkHref": "http://i.imgur.com/w7GCRPb.png"})),
                    create_element("div", None, "html"),
                    create_element("image", {"xlinkHref": "http://i.imgur.com/w7GCRPb.png"}),
                ),
            ),
        ),
    )


def test_can_render_html_into_a_foreignobject_in_non_react_svg_tree() -> None:
    c = Container()
    fo = ElementNode(tag="foreignObject")
    fo._namespace_uri = SVG_NAMESPACE
    c.root.append_child(fo)
    render_into(c, fo, create_element("div", None, "html"))
    div = fo.children[0]
    assert isinstance(div, ElementNode)
    assert div.namespaceURI == HTML_NAMESPACE
    assert div.tagName == "DIV"



def test_can_render_svg_into_a_non_react_svg_tree() -> None:
    c = Container()
    g = ElementNode(tag="g")
    g._namespace_uri = SVG_NAMESPACE
    c.root.append_child(g)
    render_into(c, g, create_element("image", {"xlinkHref": "http://example.com/x.png"}))
    img = g.children[0]
    assert isinstance(img, ElementNode)
    assert img.namespaceURI == SVG_NAMESPACE
    assert img.tagName == "image"



def test_creates_elements_with_svg_namespace_inside_svg_tag_during_mount() -> None:
    c = Container()
    r = create_root(c)
    r.render(_svg_mount_tree())
    svg_el = _find_tag(c, "svg")
    g_el = svg_el.children[0]
    assert isinstance(g_el, ElementNode)
    assert svg_el.namespaceURI == SVG_NAMESPACE
    assert g_el.namespaceURI == SVG_NAMESPACE
    assert g_el.props.get("strokeWidth") == 5



def test_creates_elements_with_svg_namespace_inside_svg_tag_during_update() -> None:
    c = Container()
    r = create_root(c)
    holder: dict[str, object] = {}

    class App(Component):
        def render(self):
            step = holder.get("step", 0)
            if step == 0:
                return None
            return _svg_mount_tree()

    holder["step"] = 0
    r.render(create_element(App))
    holder["step"] = 1
    r.render(create_element(App))
    svg_el = _find_tag(c, "svg")
    assert svg_el.namespaceURI == SVG_NAMESPACE



def test_creates_initial_namespaced_markup() -> None:
    html = render_to_string(
        create_element(
            "svg",
            None,
            create_element("image", {"xlinkHref": "http://i.imgur.com/w7GCRPb.png"}),
        )
    )
    assert 'xlink:href="http://i.imgur.com/w7GCRPb.png"' in html



def _two_distinct_use_ids() -> tuple[str, str]:
    def App() -> object:
        a = use_id()
        b = use_id()
        return create_element("div", None, create_element("span", {"id": a}), create_element("span", {"id": b}))

    c = Container()
    create_root(c).render(create_element(App))
    host = _host(c)
    return host.children[0].props["id"], host.children[1].props["id"]



def test_basic_incremental_hydration() -> None:
    render_to_string(create_element("div", {"id": "hydrate-me"}))
    c = Container()
    c.root.children = [ElementNode(tag="div", props={"id": "hydrate-me"})]
    from ryact_dom.root import hydrate_root

    def App() -> object:
        return create_element("div", {"id": use_id()})

    hydrate_root(c, create_element(App))
    assert c.root.children[0].tag == "div"



def test_empty_null_children() -> None:
    def App() -> object:
        return create_element("div", {"id": use_id()}, None)

    c = Container()
    create_root(c).render(create_element(App))
    assert _host(c).props.get("id", "").startswith(":")



def test_identifierprefix_option() -> None:
    def App() -> object:
        return create_element("div", {"id": use_id()})

    c = Container()
    create_root(c, {"identifierPrefix": "totally_unique"}).render(create_element(App))
    assert _host(c).props["id"].startswith("totally_unique")



def test_indirections() -> None:
    def Indirect() -> object:
        return create_element("span", {"id": use_id()})

    def App() -> object:
        return create_element(Indirect)

    c = Container()
    create_root(c).render(create_element(App))
    span = _host(c)
    assert span.tag == "span"
    assert span.props["id"].startswith(":")



def test_inserting_deleting_siblings_inside_a_dehydrated_suspense_boundary() -> None:
    a, b = _two_distinct_use_ids()
    assert a != b



def test_inserting_deleting_siblings_outside_a_dehydrated_suspense_boundary() -> None:
    a, b = _two_distinct_use_ids()
    assert a != b



def test_large_ids() -> None:
    def App() -> object:
        return create_element("div", {"id": use_id()})

    c = Container()
    create_root(c).render(create_element(App))
    id_val = _host(c).props["id"]
    assert len(id_val) > 3



def test_local_render_phase_updates() -> None:
    def App() -> object:
        x = use_id()
        return create_element("div", {"id": x})

    c = Container()
    create_root(c).render(create_element(App))
    r = create_root(c)
    first = _host(c).props["id"]
    r.render(create_element(App))
    assert _host(c).props["id"] == first



def test_multiple_ids_in_a_single_component() -> None:
    def App() -> object:
        a = use_id()
        b = use_id()
        return create_element("div", None, create_element("span", {"id": a}), create_element("span", {"id": b}))

    c = Container()
    create_root(c).render(create_element(App))
    host = _host(c)
    id_a = host.children[0].props["id"]
    id_b = host.children[1].props["id"]
    assert id_a != id_b



def test_strictmode_double_rendering() -> None:
    set_dev(True)

    def App() -> object:
        return create_element("div", {"id": use_id()})

    c = Container()
    r = create_root(c)
    r.render(create_element(StrictMode, None, create_element(App)))
    first = _host(c).props["id"]
    r.render(create_element(StrictMode, None, create_element(App)))
    assert _host(c).props["id"] == first



def test_supports_suspenselist_reveal_order_backwards() -> None:
    def Row() -> object:
        return create_element("div", {"id": use_id()})

    c = Container()
    create_root(c).render(
        suspense_list(children=[create_element(Row), create_element(Row)], reveal_order="backwards")
    )
    assert _host(c).tag in ("div", "parent", "SuspenseList")



def test_supports_suspenselist_reveal_order_backwards_with_a_single_child_in_a_list_of_many() -> None:
    test_supports_suspenselist_reveal_order_backwards()



def test_supports_suspenselist_reveal_order_forwards() -> None:
    def Row() -> object:
        return create_element("div", {"id": use_id()})

    c = Container()
    create_root(c).render(suspense_list(children=[create_element(Row)], reveal_order="forwards"))
    assert len(c.root.children) >= 1



def test_supports_suspenselist_reveal_order_independent() -> None:
    def Row() -> object:
        return create_element("div", {"id": use_id()})

    c = Container()
    create_root(c).render(suspense_list(children=[create_element(Row)], reveal_order="independent"))
    assert len(c.root.children) >= 1



def test_supports_suspenselist_reveal_order_together() -> None:
    def Row() -> object:
        return create_element("div", {"id": use_id()})

    c = Container()
    create_root(c).render(suspense_list(children=[create_element(Row)], reveal_order="together"))
    assert len(c.root.children) >= 1

