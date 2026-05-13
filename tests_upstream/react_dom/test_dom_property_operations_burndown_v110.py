# Translated: DOMPropertyOperations-test.js — delegated ``onChange`` from ``input``/``textarea`` (burndown v110)
from __future__ import annotations

from ryact import create_element
from ryact_dom.dom import Container, ElementNode, SyntheticEvent
from ryact_dom.root import create_root


def test_div_onchange_oninput_with_input_child_delegates_change_once() -> None:
    """Upstream: child ``input`` runs parent ``onInput``/``onChange`` once; ``change`` does not repeat ``onChange``."""

    changes = 0
    inputs = 0

    def on_change(_: SyntheticEvent) -> None:
        nonlocal changes
        changes += 1

    def on_input(_: SyntheticEvent) -> None:
        nonlocal inputs
        inputs += 1

    c = Container()
    root = create_root(c)
    root.render(
        create_element(
            "div",
            {
                "onChange": on_change,
                "onInput": on_input,
                "children": [create_element("input", {})],
            },
        )
    )
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    child = host.children[0]
    assert isinstance(child, ElementNode)
    child.dispatch_event("input")
    assert inputs == 1
    assert changes == 1
    child.dispatch_event("change")
    assert inputs == 1
    assert changes == 1


def test_div_onchange_oninput_with_textarea_child_delegates_change_once() -> None:
    changes = 0
    inputs = 0

    def on_change(_: SyntheticEvent) -> None:
        nonlocal changes
        changes += 1

    def on_input(_: SyntheticEvent) -> None:
        nonlocal inputs
        inputs += 1

    c = Container()
    root = create_root(c)
    root.render(
        create_element(
            "div",
            {
                "onChange": on_change,
                "onInput": on_input,
                "children": [create_element("textarea", {})],
            },
        )
    )
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    child = host.children[0]
    assert isinstance(child, ElementNode)
    child.dispatch_event("input")
    assert inputs == 1
    assert changes == 1
    child.dispatch_event("change")
    assert inputs == 1
    assert changes == 1
