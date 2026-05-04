from __future__ import annotations

from collections.abc import Callable

from ryact import create_element
from ryact_dom.dom import Container, ElementNode, SyntheticEvent
from ryact_dom.root import create_root


def _mk_handler(log: list[str], label: str) -> Callable[[SyntheticEvent], None]:
    def handler(e: SyntheticEvent) -> None:
        log.append(f"{label}:{e.type}:{e.target.tag}:{e.current_target.tag if e.current_target else 'none'}")

    return handler


def test_custom_elements_do_not_treat_non_function_on_props_as_listeners() -> None:
    c = Container()
    root = create_root(c)
    root.render(create_element("my-custom-element", {"onClick": "not-a-fn"}))
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    assert host._listeners == {}
    assert host.props.get("onClick") == "not-a-fn"


def test_custom_element_custom_event_with_dash_in_name() -> None:
    log: list[str] = []
    c = Container()
    root = create_root(c)
    root.render(create_element("my-custom-element", {"onmy-event": _mk_handler(log, "h")}))
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    host.dispatch_event("my-event")
    assert log == ["h:my-event:my-custom-element:my-custom-element"]


def test_custom_element_custom_events_lowercase_and_uppercase_map_to_lowercase_event_type() -> None:
    log: list[str] = []
    c = Container()
    root = create_root(c)
    root.render(
        create_element(
            "my-custom-element",
            {
                "oncustomevent": _mk_handler(log, "lc"),
                "onCustomEvent": _mk_handler(log, "uc"),
            },
        )
    )
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    host.dispatch_event("customevent")
    assert log == [
        "lc:customevent:my-custom-element:my-custom-element",
        "uc:customevent:my-custom-element:my-custom-element",
    ]


def test_custom_element_remove_event_handler() -> None:
    log: list[str] = []
    c = Container()
    root = create_root(c)
    root.render(create_element("my-custom-element", {"onClick": _mk_handler(log, "a")}))
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    host.dispatch_event("click")
    assert log

    log.clear()
    root.render(create_element("my-custom-element", {"onClick": None}))
    host2 = c.root.children[0]
    assert isinstance(host2, ElementNode)
    host2.dispatch_event("click")
    assert log == []


def test_custom_elements_can_remove_and_readd_custom_event_listeners() -> None:
    log: list[str] = []
    c = Container()
    root = create_root(c)
    h = _mk_handler(log, "h")

    root.render(create_element("my-custom-element", {"onCustomEvent": h}))
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    host.dispatch_event("customevent")
    assert log

    log.clear()
    root.render(create_element("my-custom-element", {"onCustomEvent": None}))
    host2 = c.root.children[0]
    assert isinstance(host2, ElementNode)
    host2.dispatch_event("customevent")
    assert log == []

    root.render(create_element("my-custom-element", {"onCustomEvent": h}))
    host3 = c.root.children[0]
    assert isinstance(host3, ElementNode)
    host3.dispatch_event("customevent")
    assert log == ["h:customevent:my-custom-element:my-custom-element"]


def test_custom_elements_support_custom_event_capture_prop_as_distinct_event_type() -> None:
    log: list[str] = []
    c = Container()
    root = create_root(c)
    root.render(create_element("my-custom-element", {"onCustomEventCapture": _mk_handler(log, "cap")}))
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    host.dispatch_event("customeventcapture")
    assert log == ["cap:customeventcapture:my-custom-element:my-custom-element"]


def test_custom_elements_keep_separate_oninput_and_onchange_listeners() -> None:
    log: list[str] = []
    c = Container()
    root = create_root(c)
    root.render(
        create_element(
            "my-custom-element",
            {"onInput": _mk_handler(log, "i"), "onChange": _mk_handler(log, "c")},
        )
    )
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    host.dispatch_event("input")
    host.dispatch_event("change")
    assert log == [
        "i:input:my-custom-element:my-custom-element",
        "c:change:my-custom-element:my-custom-element",
    ]


def test_custom_elements_onclick_bubbles_from_child_div() -> None:
    log: list[str] = []
    c = Container()
    root = create_root(c)
    root.render(
        create_element(
            "my-custom-element",
            {"onClick": _mk_handler(log, "h"), "children": [create_element("div", {})]},
        )
    )
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    child = host.children[0]
    assert isinstance(child, ElementNode)
    child.dispatch_event("click")
    assert log == ["h:click:div:my-custom-element"]


def test_custom_elements_onchange_oninput_bubble_from_child_input() -> None:
    log: list[str] = []
    c = Container()
    root = create_root(c)
    root.render(
        create_element(
            "my-custom-element",
            {
                "onInput": _mk_handler(log, "i"),
                "onChange": _mk_handler(log, "c"),
                "children": [create_element("input", {})],
            },
        )
    )
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    child = host.children[0]
    assert isinstance(child, ElementNode)
    child.dispatch_event("input")
    child.dispatch_event("change")
    assert log == [
        "i:input:input:my-custom-element",
        "c:change:input:my-custom-element",
    ]


def test_div_onchange_oninput_onclick_bubble_from_child_div() -> None:
    log: list[str] = []
    c = Container()
    root = create_root(c)
    root.render(
        create_element(
            "div",
            {
                "onInput": _mk_handler(log, "i"),
                "onChange": _mk_handler(log, "c"),
                "onClick": _mk_handler(log, "k"),
                "children": [create_element("div", {})],
            },
        )
    )
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    child = host.children[0]
    assert isinstance(child, ElementNode)
    child.dispatch_event("input")
    child.dispatch_event("change")
    child.dispatch_event("click")
    assert log == [
        "i:input:div:div",
        "c:change:div:div",
        "k:click:div:div",
    ]


def test_custom_element_custom_event_handlers_assign_multiple_types() -> None:
    log: list[str] = []
    c = Container()
    root = create_root(c)
    root.render(create_element("my-custom-element", {"onCustomEvent": "not-a-fn"}))
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    assert host._listeners == {}
    assert host.props.get("onCustomEvent") == "not-a-fn"

    root.render(create_element("my-custom-element", {"onCustomEvent": _mk_handler(log, "h")}))
    host2 = c.root.children[0]
    assert isinstance(host2, ElementNode)
    host2.dispatch_event("customevent")
    assert log == ["h:customevent:my-custom-element:my-custom-element"]
