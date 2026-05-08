# Translated subset: ReactDOMSelect-test.js — controlled → uncontrolled memory, nested legacy render bridge
from __future__ import annotations

from collections.abc import Iterator

import pytest
from ryact import create_element
from ryact_dom.dom import Container, ElementNode, SyntheticEvent, TextNode
from ryact_dom.root import create_root, render_into


@pytest.fixture(autouse=True)
def _dev_only_guards() -> Iterator[None]:
    yield


def _animal_options() -> tuple:
    return (
        create_element("option", {"value": "monkey"}, "A monkey!"),
        create_element("option", {"value": "giraffe"}, "A giraffe!"),
        create_element("option", {"value": "gorilla"}, "A gorilla!"),
    )


def _options_selected_pairs(container: Container) -> list[tuple[str, bool]]:
    sel = container.root.children[0]
    assert isinstance(sel, ElementNode)
    assert sel.tag.lower() == "select"
    out: list[tuple[str, bool]] = []

    def walk(node: ElementNode) -> None:
        for ch in node.children:
            if isinstance(ch, ElementNode) and ch.tag.lower() == "option":
                v = ch.props.get("value")
                if v is None and ch.children and isinstance(ch.children[0], TextNode):
                    v = ch.children[0].text
                sv = "" if v is None else str(v)
                out.append((sv, bool(ch.props.get("selected"))))
            elif isinstance(ch, ElementNode) and ch.tag.lower() == "optgroup":
                walk(ch)

    walk(sel)
    return out


def test_remembers_value_when_switching_to_uncontrolled_c77aff62() -> None:
    c = Container()
    root = create_root(c)
    stub = create_element(
        "select",
        {"value": "giraffe", "onChange": lambda _e: None},
        *_animal_options(),
    )
    options = stub.props.get("children", ())
    root.render(stub)
    assert _options_selected_pairs(c) == [
        ("monkey", False),
        ("giraffe", True),
        ("gorilla", False),
    ]

    root.render(create_element("select", {}, *options))
    assert _options_selected_pairs(c) == [
        ("monkey", False),
        ("giraffe", True),
        ("gorilla", False),
    ]


def test_remembers_updated_value_when_switching_to_uncontrolled_01fdbf73() -> None:
    c = Container()
    root = create_root(c)
    stub = create_element(
        "select",
        {"value": "giraffe", "onChange": lambda _e: None},
        *_animal_options(),
    )
    options = stub.props.get("children", ())
    root.render(stub)
    root.render(
        create_element(
            "select",
            {"value": "gorilla", "onChange": lambda _e: None},
            *options,
        ),
    )
    assert _options_selected_pairs(c) == [
        ("monkey", False),
        ("giraffe", False),
        ("gorilla", True),
    ]

    root.render(create_element("select", {}, *options))
    assert _options_selected_pairs(c) == [
        ("monkey", False),
        ("giraffe", False),
        ("gorilla", True),
    ]


def test_nested_legacy_render_controls_value_af2f2ec8() -> None:
    c = Container()
    root = create_root(c)
    root.render(create_element("div", {}))
    nest = c.root.children[0]
    assert isinstance(nest, ElementNode)
    state = {"v": "giraffe"}
    opts = _animal_options()

    def inner() -> object:
        def _on_change(e: SyntheticEvent) -> None:
            state["v"] = e.target.value
            render_into(c, nest, inner())

        return create_element(
            "select",
            {"value": state["v"], "onChange": _on_change},
            *opts,
        )

    render_into(c, nest, inner())
    sel = nest.children[0]
    assert isinstance(sel, ElementNode)
    assert sel.tag.lower() == "select"
    assert sel.value == "giraffe"

    sel.value = "gorilla"
    sel.dispatch_event("input")
    assert sel.value == "gorilla"
    sel.dispatch_event("change")
    assert sel.value == "gorilla"
