"""ReactDOMComponent-test.js parity: iOS tap, mount events, nesting refs, unmount (v137)."""

from __future__ import annotations

import warnings
from collections.abc import Iterator

import pytest
from ryact import Component, create_element, create_portal
from ryact.dev import is_dev
from ryact_dom.dom import Container, ElementNode
from ryact_dom.dom_internals import find_dom_node, reset_component_dom_registry
from ryact_dom.event_listener import add_document_event_listener, reset_document_listener_test_state
from ryact_dom.html_props import reset_dom_warning_state
from ryact_dom.root import create_root
from ryact_dom.server import render_to_string
from ryact_dom.validate_dom_nesting import reset_validate_dom_nesting_dev_state


@pytest.fixture(autouse=True)
def _reset_state() -> Iterator[None]:
    reset_dom_warning_state()
    reset_validate_dom_nesting_dev_state()
    reset_document_listener_test_state()
    reset_component_dom_registry()
    yield


def _host(c: Container) -> ElementNode:
    h = c.root.children[0]
    assert isinstance(h, ElementNode)
    return h


def _warn_msgs(rec: list[warnings.WarningMessage]) -> list[str]:
    return [str(w.message) for w in rec]


def _assert_has_at_star(msgs: list[str], needle: str) -> None:
    assert any(needle in m and "(at **)" in m for m in msgs), msgs


@pytest.mark.skipif(not is_dev(), reason="iOS tap onclick is DEV parity")
def test_adds_onclick_handler_to_elements_with_onclick_prop() -> None:
    c = Container()
    r = create_root(c)

    def _on_click(_e: object) -> None:
        return None

    r.render(create_element("div", {"onClick": _on_click}))
    assert callable(_host(c).onclick)


def test_adds_onclick_handler_to_a_portal_root() -> None:
    portal_c = Container()
    c = Container()
    r = create_root(c)

    def _on_click(_e: object) -> None:
        return None

    r.render(
        create_portal(
            children=create_element("div", {"onClick": _on_click}),
            container=portal_c,
        ),
    )
    assert callable(portal_c.onclick)


@pytest.mark.skipif(not is_dev(), reason="legacy ReactDOM.render roots are out of scope")
def test_does_not_add_onclick_handler_to_the_react_root_in_legacy_mode() -> None:
    c = Container()
    r = create_root(c)

    def _on_click(_e: object) -> None:
        return None

    r.render(create_element("div", {"onClick": _on_click}))
    assert getattr(c, "onclick", None) is None


def test_should_receive_a_load_event_on_link_elements() -> None:
    log: list[str] = []
    c = Container()
    r = create_root(c)
    r.render(create_element("link", {"onLoad": lambda _e: log.append("load")}))
    link = c.root.children[0]
    assert isinstance(link, ElementNode)
    link.dispatch_event("load")
    assert log == ["load"]


def test_should_receive_an_error_event_on_link_elements() -> None:
    log: list[str] = []
    c = Container()
    r = create_root(c)
    r.render(create_element("link", {"onError": lambda _e: log.append("error")}))
    link = c.root.children[0]
    assert isinstance(link, ElementNode)
    link.dispatch_event("error")
    assert log == ["error"]


def test_should_support_custom_elements_which_extend_native_elements() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("div", {"is": "custom-div"}))
    host = _host(c)
    assert host._document_create_options == {"is": "custom-div"}
    inserts = [op for op in c.ops if op.get("op") == "insert"]
    assert any(op.get("createOptions") == {"is": "custom-div"} for op in inserts)


def test_should_work_error_event_on_source_element() -> None:
    log: list[str] = []
    c = Container()
    r = create_root(c)
    r.render(
        create_element(
            "video",
            None,
            create_element("source", {"onError": lambda _e: log.append("onError")}),
        ),
    )
    source = c.root.children[0].children[0]
    assert isinstance(source, ElementNode)
    source.dispatch_event("error")
    assert log == ["onError"]


def test_should_work_load_and_error_events_on_image_element_in_svg() -> None:
    log: list[str] = []
    c = Container()
    r = create_root(c)
    r.render(
        create_element(
            "svg",
            None,
            create_element(
                "image",
                {
                    "onError": lambda _e: log.append("onError"),
                    "onLoad": lambda _e: log.append("onLoad"),
                },
            ),
        ),
    )
    svg = _host(c)
    image = svg.children[0]
    assert isinstance(image, ElementNode)
    image.dispatch_event("error")
    image.dispatch_event("load")
    assert log == ["onError", "onLoad"]


@pytest.mark.skipif(not is_dev(), reason="unknown prop DEV warnings")
def test_gives_source_code_refs_for_unknown_prop_warning() -> None:
    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("div", {"class": "x"}))
    _assert_has_at_star(_warn_msgs(rec), "Invalid DOM property `class`")
    with warnings.catch_warnings(record=True) as rec2:
        warnings.simplefilter("always")
        r.render(create_element("input", {"onclick": lambda _e: None}))
    _assert_has_at_star(_warn_msgs(rec2), "Invalid event handler property `onclick`")


@pytest.mark.skipif(not is_dev(), reason="unknown prop DEV warnings")
def test_gives_source_code_refs_for_unknown_prop_warning_ssr() -> None:
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        render_to_string(create_element("div", {"class": "x"}))
    _assert_has_at_star(_warn_msgs(rec), "Invalid DOM property `class`")
    rec.clear()
    with warnings.catch_warnings(record=True) as rec2:
        warnings.simplefilter("always")
        render_to_string(create_element("input", {"oninput": lambda _e: None}))
    _assert_has_at_star(_warn_msgs(rec2), "Invalid event handler property `oninput`")


@pytest.mark.skipif(not is_dev(), reason="unknown prop DEV warnings")
def test_gives_source_code_refs_for_unknown_prop_warning_for_update_render() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("div", None))
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("div", {"class": "x"}))
    _assert_has_at_star(_warn_msgs(rec), "Invalid DOM property `class`")


@pytest.mark.skipif(not is_dev(), reason="unknown prop DEV warnings")
def test_gives_source_code_refs_for_unknown_prop_warning_for_exact_elements() -> None:
    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(
            create_element(
                "div",
                None,
                create_element("span", {"class": "a"}),
                create_element("strong", {"onclick": lambda _e: None}),
            ),
        )
    msgs = _warn_msgs(rec)
    _assert_has_at_star(msgs, "Invalid DOM property `class`")
    _assert_has_at_star(msgs, "Invalid event handler property `onclick`")


@pytest.mark.skipif(not is_dev(), reason="unknown prop DEV warnings")
def test_gives_source_code_refs_for_unknown_prop_warning_for_exact_elements_ssr() -> None:
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        render_to_string(
            create_element(
                "div",
                None,
                create_element("span", {"class": "a"}),
                create_element("strong", {"onclick": lambda _e: None}),
            ),
        )
    msgs = _warn_msgs(rec)
    _assert_has_at_star(msgs, "Invalid DOM property `class`")
    _assert_has_at_star(msgs, "Invalid event handler property `onclick`")


class _Parent(Component):
    def render(self):
        return create_element(
            "div",
            None,
            create_element(_Child1, None),
            create_element(_Child2, None),
            create_element(_Child3, None),
            create_element(_Child4, None),
        )


class _Child1(Component):
    def render(self):
        return create_element("span", {"class": "c1"})


class _Child2(Component):
    def render(self):
        return create_element("strong", {"onclick": lambda _e: None})


class _Child3(Component):
    def render(self):
        return create_element("em", {"class": "c3"})


class _Child4(Component):
    def render(self):
        return create_element("b", {"onclick": lambda _e: None})


@pytest.mark.skipif(not is_dev(), reason="unknown prop DEV warnings")
def test_gives_source_code_refs_for_unknown_prop_warning_for_exact_elements_in_composition() -> None:
    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element(_Parent, None))
    msgs = _warn_msgs(rec)
    assert sum("Invalid DOM property `class`" in m for m in msgs) >= 2
    assert sum("Invalid event handler property `onclick`" in m for m in msgs) >= 2
    assert all("(at **)" in m for m in msgs if "Invalid DOM property" in m or "Invalid event handler" in m)


@pytest.mark.skipif(not is_dev(), reason="unknown prop DEV warnings")
def test_gives_source_code_refs_for_unknown_prop_warning_for_exact_elements_in_composition_ssr() -> None:
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        render_to_string(create_element(_Parent, None))
    msgs = _warn_msgs(rec)
    assert sum("Invalid DOM property `class`" in m for m in msgs) >= 2
    assert sum("Invalid event handler property `onclick`" in m for m in msgs) >= 2


class _Row(Component):
    def render(self):
        return create_element("tr", None, "x")


class _FancyRow(Component):
    def render(self):
        return create_element("tr", None, "y")


@pytest.mark.skipif(not is_dev(), reason="nesting DEV warnings")
def test_gives_useful_context_in_warnings() -> None:
    def viz1():
        return create_element("table", None, create_element(_FancyRow, None))

    def app1():
        return create_element("div", None, create_element(viz1, None))

    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element(app1, None))
    msgs = _warn_msgs(rec)
    assert any("in tr (at **)" in m and "in _FancyRow" in m for m in msgs), msgs
    assert any("in table (at **)" in m for m in msgs), msgs


class _Table(Component):
    def render(self):
        return create_element("table", None, self.props["children"])


class _FancyTable(Component):
    def render(self):
        return create_element("table", None, self.props["children"])


@pytest.mark.skipif(not is_dev(), reason="nesting DEV warnings")
def test_gives_useful_context_in_warnings_2() -> None:
    def viz2():
        return create_element(_FancyTable, None, create_element(_FancyRow, None))

    def app2():
        return create_element("div", None, create_element(viz2, None))

    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element(app2, None))
    msgs = _warn_msgs(rec)
    assert any("in _FancyTable (at **)" in m for m in msgs), msgs


@pytest.mark.skipif(not is_dev(), reason="nesting DEV warnings")
def test_gives_useful_context_in_warnings_3() -> None:
    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(
            create_element(
                _FancyTable,
                None,
                create_element(_FancyRow, None),
            ),
        )
    msgs = _warn_msgs(rec)
    assert any("in tr (at **)" in m for m in msgs), msgs


@pytest.mark.skipif(not is_dev(), reason="nesting DEV warnings")
def test_gives_useful_context_in_warnings_4() -> None:
    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("table", None, create_element(_FancyRow, None)))
    msgs = _warn_msgs(rec)
    assert any("in tr (at **)" in m for m in msgs), msgs


@pytest.mark.skipif(not is_dev(), reason="nesting DEV warnings")
def test_gives_useful_context_in_warnings_5() -> None:
    class _Link(Component):
        def render(self):
            return create_element("a", None, self.props["children"])

    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(
            create_element(
                _FancyTable,
                None,
                create_element("tr", None, create_element("td", None, "cell")),
            ),
        )
    msgs = _warn_msgs(rec)
    assert any("in tr (at **)" in m for m in msgs), msgs
    assert any("in table (at **)" in m for m in msgs), msgs
    c2 = Container()
    r2 = create_root(c2)
    with warnings.catch_warnings(record=True) as rec2:
        warnings.simplefilter("always")
        r2.render(create_element("p", None, create_element("p", None, "nested")))
    msgs2 = _warn_msgs(rec2)
    assert any("in p (at **)" in m for m in msgs2), msgs2
    assert any("cannot be a descendant of <p>" in m for m in msgs2), msgs2


def test_receives_events_in_specific_order() -> None:
    order: list[str] = []

    def track(label: str):
        return lambda _e: order.append(label)

    c = Container()
    r = create_root(c)
    r.render(
        create_element(
            "div",
            {
                "onClickCapture": track("outer capture"),
                "onClick": track("outer bubble"),
            },
            create_element(
                "button",
                {
                    "onClickCapture": track("inner capture"),
                    "onClick": track("inner bubble"),
                },
                "go",
            ),
        ),
    )
    inner_host = _host(c).children[0]
    assert isinstance(inner_host, ElementNode)

    add_document_event_listener("click", track("document bubble"), capture=False)
    add_document_event_listener("click", track("document capture"), capture=True)

    inner_host.dispatch_event("click")
    assert order == [
        "document capture",
        "outer capture",
        "inner capture",
        "inner bubble",
        "outer bubble",
        "document bubble",
    ]


class _Inner(Component):
    def componentWillUnmount(self) -> None:
        node = find_dom_node(self)
        assert node is not None
        assert node.nodeName == "SPAN"

    def render(self):
        return create_element("span", None, "x")


class _Outer(Component):
    def render(self):
        return create_element("div", None, create_element(_Inner, None))


def test_unmounts_children_before_unsetting_dom_node_info() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element(_Outer, None))
    r.unmount()


def test_should_allow_named_slot_projection_on_both_web_components_and_regular_dom_elements() -> None:
    c = Container()
    r = create_root(c)
    r.render(
        create_element(
            "my-element",
            None,
            create_element("span", {"slot": "first"}, "Hello"),
            create_element("span", {"slot": "second"}, "World"),
        ),
    )
    host = _host(c)
    slots = [ch.get_attribute("slot") for ch in host.children if isinstance(ch, ElementNode)]
    assert slots == ["first", "second"]
