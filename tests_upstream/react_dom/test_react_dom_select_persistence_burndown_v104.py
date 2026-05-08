# Translated subset: ReactDOMSelect-test.js — uncontrolled persistence, re-add options,
# controlled change refresh, unmount during onChange
from __future__ import annotations

from collections.abc import Iterator

import pytest
from ryact import create_element
from ryact_dom.dom import Container, ElementNode, TextNode
from ryact_dom.root import create_root


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


def _single_select_value(container: Container) -> str:
    for val, sel in _options_selected_pairs(container):
        if sel:
            return val
    return ""


def test_uncontrolled_defaultvalue_does_not_reset_user_dom_value_2fb789aa() -> None:
    c = Container()
    root = create_root(c)
    stub = create_element("select", {"defaultValue": "giraffe"}, *_animal_options())
    root.render(stub)
    assert _single_select_value(c) == "giraffe"

    sel = c.root.children[0]
    assert isinstance(sel, ElementNode)
    for ch in sel.children:
        if isinstance(ch, ElementNode) and ch.tag.lower() == "option":
            v = ch.props.get("value")
            if v == "monkey":
                ch.props["selected"] = True
            else:
                ch.props.pop("selected", None)

    assert _single_select_value(c) == "monkey"
    root.render(stub)
    assert _single_select_value(c) == "monkey"


def test_uncontrolled_multiple_defaultvalue_not_reapplied_after_options_return_ce4089f9() -> None:
    c = Container()
    root = create_root(c)
    full = (
        create_element("option", {"value": "monkey"}, "A monkey!"),
        create_element("option", {"value": "giraffe"}, "A giraffe!"),
        create_element("option", {"value": "gorilla"}, "A gorilla!"),
    )
    root.render(
        create_element(
            "select",
            {"multiple": True, "defaultValue": ["giraffe"]},
            *full,
        ),
    )
    assert _options_selected_pairs(c) == [
        ("monkey", False),
        ("giraffe", True),
        ("gorilla", False),
    ]

    root.render(
        create_element(
            "select",
            {"multiple": True, "defaultValue": ["giraffe"]},
            create_element("option", {"value": "monkey"}, "A monkey!"),
            create_element("option", {"value": "gorilla"}, "A gorilla!"),
        ),
    )
    assert _options_selected_pairs(c) == [("monkey", False), ("gorilla", False)]

    root.render(
        create_element(
            "select",
            {"multiple": True, "defaultValue": ["giraffe"]},
            *full,
        ),
    )
    assert _options_selected_pairs(c) == [
        ("monkey", False),
        ("giraffe", False),
        ("gorilla", False),
    ]


def test_controlled_select_keeps_value_after_change_dispatch_be542e89() -> None:
    c = Container()
    root = create_root(c)
    stub = create_element(
        "select",
        {"value": "giraffe", "onChange": lambda _e: None},
        *_animal_options(),
    )
    root.render(stub)
    sel = c.root.children[0]
    assert isinstance(sel, ElementNode)
    sel.dispatch_event("change")
    assert _single_select_value(c) == "giraffe"


def test_change_handler_may_unmount_root_without_throwing_7f862d53() -> None:
    c = Container()
    root = create_root(c)

    def _unmount(_evt: object) -> None:
        root.unmount()

    stub = create_element("select", {"onChange": _unmount}, *_animal_options())
    root.render(stub)
    sel = c.root.children[0]
    assert isinstance(sel, ElementNode)
    sel.dispatch_event("change")
    assert c.root.children == []


def test_second_unmount_throws() -> None:
    c = Container()
    root = create_root(c)
    root.render(create_element("div", None, "x"))
    root.unmount()
    with pytest.raises(RuntimeError, match="unmounted"):
        root.unmount()
