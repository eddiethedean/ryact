# Translated: DOMPropertyOperations-test.js — custom ``on*`` + ``defineProperty`` ``in`` heuristic (v114)
from __future__ import annotations

from ryact import create_element
from ryact_dom.dom import Container, ElementNode, SyntheticEvent
from ryact_dom.root import create_root


def test_custom_element_custom_event_handlers_assign_multiple_types_with_setter() -> None:
    """Upstream ``defineProperty`` on ``oncustomevent``: use ``set_custom_on_listener_property_mode``."""

    calls: list[None] = []

    def h(_: SyntheticEvent) -> None:
        calls.append(None)

    c = Container()
    root = create_root(c)
    root.render(create_element("my-custom-element", {}))
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    host.set_custom_on_listener_property_mode("customevent")

    root.render(create_element("my-custom-element", {"onCustomEvent": h}))
    h1 = c.root.children[0]
    assert isinstance(h1, ElementNode)
    assert h1.props.get("onCustomEvent") is None
    h1.dispatch_event("customevent")
    assert len(calls) == 1

    root.render(create_element("my-custom-element", {"onCustomEvent": "foo"}))
    h2 = c.root.children[0]
    assert isinstance(h2, ElementNode)
    h2.dispatch_event("customevent")
    assert len(calls) == 1
    assert h2.props.get("onCustomEvent") == "foo"

    root.render(create_element("my-custom-element", {"onCustomEvent": h}))
    h3 = c.root.children[0]
    assert isinstance(h3, ElementNode)
    h3.dispatch_event("customevent")
    assert len(calls) == 2
    assert h3.props.get("onCustomEvent") is None

    root.render(create_element("my-custom-element", {}))
    h4 = c.root.children[0]
    assert isinstance(h4, ElementNode)
    h4.dispatch_event("customevent")
    assert len(calls) == 2
    assert "onCustomEvent" not in h4.props
