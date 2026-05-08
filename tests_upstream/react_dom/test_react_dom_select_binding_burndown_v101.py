# Translated subset: ReactDOMSelect-test.js — select value / defaultValue / option selected binding
from __future__ import annotations

import re
import warnings
from collections.abc import Iterator

import pytest
from ryact import create_element
from ryact.dev import is_dev
from ryact_dom.dom import Container, ElementNode, TextNode
from ryact_dom.root import create_root
from ryact_dom.server import render_to_string


@pytest.fixture(autouse=True)
def _dev_only_guards() -> Iterator[None]:
    yield


def _options_from_dom(container: Container) -> list[tuple[str, bool]]:
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


def _animal_options():
    return (
        create_element("option", {"value": "monkey"}, "A monkey!"),
        create_element("option", {"value": "giraffe"}, "A giraffe!"),
        create_element("option", {"value": "gorilla"}, "A gorilla!"),
    )


def test_default_value_selects_matching_option() -> None:
    c = Container()
    root = create_root(c)
    root.render(create_element("select", {"defaultValue": "giraffe"}, _animal_options()))
    opts = _options_from_dom(c)
    assert opts == [("monkey", False), ("giraffe", True), ("gorilla", False)]


def test_value_prop_controls_selection() -> None:
    c = Container()
    root = create_root(c)
    root.render(
        create_element(
            "select",
            {"value": "giraffe", "onChange": lambda e: None},
            _animal_options(),
        ),
    )
    opts = _options_from_dom(c)
    assert opts[1][1] is True


def test_value_updates_controlled_selection() -> None:
    c = Container()
    root = create_root(c)
    opts_el = _animal_options()
    root.render(
        create_element("select", {"value": "giraffe", "onChange": lambda e: None}, opts_el),
    )
    assert _options_from_dom(c)[2][0] == "gorilla"
    root.render(
        create_element("select", {"value": "gorilla", "onChange": lambda e: None}, opts_el),
    )
    assert _options_from_dom(c)[2][1] is True
    assert _options_from_dom(c)[1][1] is False


def test_default_value_multiple() -> None:
    c = Container()
    root = create_root(c)
    root.render(
        create_element(
            "select",
            {"defaultValue": ("giraffe", "gorilla"), "multiple": True},
            _animal_options(),
        ),
    )
    opts = _options_from_dom(c)
    assert opts[0][1] is False and opts[1][1] is True and opts[2][1] is True


def test_value_multiple() -> None:
    c = Container()
    root = create_root(c)
    root.render(
        create_element(
            "select",
            {"value": ["giraffe", "gorilla"], "multiple": True, "onChange": lambda e: None},
            _animal_options(),
        ),
    )
    opts = _options_from_dom(c)
    assert opts[0][1] is False and opts[1][1] is True and opts[2][1] is True


def test_first_non_disabled_option_selected_by_default() -> None:
    c = Container()
    root = create_root(c)
    root.render(
        create_element(
            "select",
            None,
            create_element("option", {"value": "0", "disabled": True}, "Disabled"),
            create_element("option", {"value": "1", "disabled": True}, "Still Disabled"),
            create_element("option", {"value": "2"}, "0"),
            create_element("option", {"value": "3", "disabled": True}, "Also Disabled"),
        ),
    )
    opts = _options_from_dom(c)
    assert opts[0][1] is False and opts[1][1] is False and opts[2][1] is True and opts[3][1] is False


def test_proto_string_value_single() -> None:
    c = Container()
    root = create_root(c)
    root.render(
        create_element(
            "select",
            {"value": "__proto__", "onChange": lambda e: None},
            create_element("option", {"value": "monkey"}),
            create_element("option", {"value": "__proto__"}),
            create_element("option", {"value": "gorilla"}),
        ),
    )
    opts = _options_from_dom(c)
    assert opts[1][1] is True


def test_proto_string_value_multiple() -> None:
    c = Container()
    root = create_root(c)
    root.render(
        create_element(
            "select",
            {"value": ["__proto__", "gorilla"], "multiple": True, "onChange": lambda e: None},
            create_element("option", {"value": "monkey"}),
            create_element("option", {"value": "__proto__"}),
            create_element("option", {"value": "gorilla"}),
        ),
    )
    opts = _options_from_dom(c)
    assert opts[0][1] is False and opts[1][1] is True and opts[2][1] is True


class _ObjVal:
    def __str__(self) -> str:
        return "giraffe"


def test_object_stringify_value() -> None:
    c = Container()
    root = create_root(c)
    root.render(
        create_element(
            "select",
            {"value": _ObjVal(), "onChange": lambda e: None},
            _animal_options(),
        ),
    )
    assert _options_from_dom(c)[1][1] is True


def test_grandchild_options_in_optgroup() -> None:
    c = Container()
    root = create_root(c)
    root.render(
        create_element(
            "select",
            {"value": "b", "onChange": lambda e: None},
            create_element(
                "optgroup",
                {"label": "group"},
                create_element("option", {"value": "a"}, "a"),
                create_element("option", {"value": "b"}, "b"),
                create_element("option", {"value": "c"}, "c"),
            ),
        ),
    )
    assert _options_from_dom(c) == [("a", False), ("b", True), ("c", False)]


def test_multiple_no_default_selects_none() -> None:
    c = Container()
    root = create_root(c)
    root.render(create_element("select", {"multiple": True}, _animal_options()))
    opts = _options_from_dom(c)
    assert all(not s for _, s in opts)


def test_size_gt_one_no_autoselect() -> None:
    c = Container()
    root = create_root(c)
    root.render(create_element("select", {"size": 3}, _animal_options()))
    opts = _options_from_dom(c)
    assert all(not s for _, s in opts)


def test_switch_to_multiple() -> None:
    c = Container()
    root = create_root(c)
    opts = _animal_options()
    root.render(create_element("select", {"value": "giraffe", "onChange": lambda e: None}, opts))
    root.render(
        create_element(
            "select",
            {
                "multiple": True,
                "value": ["giraffe", "gorilla"],
                "onChange": lambda e: None,
            },
            opts,
        ),
    )
    st = _options_from_dom(c)
    assert st[1][1] and st[2][1] and not st[0][1]


def test_switch_from_multiple() -> None:
    c = Container()
    root = create_root(c)
    opts = _animal_options()
    root.render(
        create_element(
            "select",
            {"multiple": True, "value": ["giraffe", "gorilla"], "onChange": lambda e: None},
            opts,
        ),
    )
    root.render(create_element("select", {"value": "gorilla", "onChange": lambda e: None}, opts))
    st = _options_from_dom(c)
    assert st[2][1] and not st[0][1] and not st[1][1]


def test_ssr_value() -> None:
    html = render_to_string(
        create_element(
            "select",
            {"value": "giraffe", "onChange": lambda e: None},
            _animal_options(),
        ),
    )
    assert re.search(r'<option[^>]*value="giraffe"[^>]*selected', html)
    assert "selected" not in html.split("monkey")[1].split("giraffe")[0]


def test_ssr_default_value_explicit() -> None:
    html = render_to_string(create_element("select", {"defaultValue": "giraffe"}, _animal_options()))
    assert 'value="giraffe"' in html


def test_ssr_multiple() -> None:
    html = render_to_string(
        create_element(
            "select",
            {"defaultValue": ("giraffe", "gorilla"), "multiple": True},
            _animal_options(),
        ),
    )
    assert html.count("selected") == 2


def test_no_throw_empty_select_with_default_value() -> None:
    c = Container()
    root = create_root(c)
    root.render(create_element("select", {"defaultValue": "x"}))


def test_no_throw_empty_select_with_value() -> None:
    c = Container()
    root = create_root(c)
    root.render(create_element("select", {"value": "x", "onChange": lambda e: None}))


def test_reset_selected_when_options_change_under_value() -> None:
    c = Container()
    root = create_root(c)
    root.render(
        create_element(
            "select",
            {"multiple": True, "value": ["a", "b"], "onChange": lambda e: None},
            create_element("option", {"value": "a"}, "a"),
            create_element("option", {"value": "b"}, "b"),
            create_element("option", {"value": "c"}, "c"),
        ),
    )
    root.render(
        create_element(
            "select",
            {"multiple": True, "value": ["a", "b"], "onChange": lambda e: None},
            create_element("option", {"value": "a"}, "a"),
            create_element("option", {"value": "c"}, "c"),
        ),
    )
    assert _options_from_dom(c) == [("a", True), ("c", False)]


@pytest.mark.skipif(not is_dev(), reason="select DEV warnings")
def test_warn_value_null() -> None:
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        render_to_string(create_element("select", {"value": None}, _animal_options()))
    assert any("value` prop on `select` should not be null" in str(w.message) for w in rec)


@pytest.mark.skipif(not is_dev(), reason="select DEV warnings")
def test_warn_value_null_multiple() -> None:
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        render_to_string(
            create_element("select", {"value": None, "multiple": True}, _animal_options()),
        )
    assert any("empty array when `multiple`" in str(w.message) for w in rec)


@pytest.mark.skipif(not is_dev(), reason="select DEV warnings")
def test_warn_value_and_default_value() -> None:
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        render_to_string(
            create_element(
                "select",
                {"value": "giraffe", "defaultValue": "monkey"},
                _animal_options(),
            ),
        )
    assert any("controlled or uncontrolled" in str(w.message) for w in rec)


@pytest.mark.skipif(not is_dev(), reason="select DEV warnings")
def test_warn_selected_on_option() -> None:
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        render_to_string(
            create_element(
                "select",
                None,
                create_element("option", {"value": "a", "selected": True}, "a"),
            ),
        )
    assert any("instead of " in str(w.message) and "selected" in str(w.message).lower() for w in rec)


@pytest.mark.skipif(not is_dev(), reason="select DEV warnings")
def test_warn_controlled_without_on_change_false() -> None:
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        render_to_string(create_element("select", {"value": False}, _animal_options()))
    assert any("onChange" in str(w.message) and "read-only" in str(w.message) for w in rec)


@pytest.mark.skipif(not is_dev(), reason="select DEV warnings")
def test_warn_controlled_without_on_change_zero() -> None:
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        render_to_string(create_element("select", {"value": 0}, _animal_options()))
    assert any("onChange" in str(w.message) for w in rec)


@pytest.mark.skipif(not is_dev(), reason="select DEV warnings")
def test_warn_controlled_without_on_change_string_zero() -> None:
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        render_to_string(create_element("select", {"value": "0"}, _animal_options()))
    assert any("onChange" in str(w.message) for w in rec)


@pytest.mark.skipif(not is_dev(), reason="select DEV warnings")
def test_warn_controlled_without_on_change_empty_string() -> None:
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        render_to_string(create_element("select", {"value": ""}, _animal_options()))
    assert any("onChange" in str(w.message) for w in rec)


@pytest.mark.skipif(not is_dev(), reason="select DEV warnings")
def test_no_warn_on_change_when_disabled() -> None:
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        render_to_string(create_element("select", {"value": "giraffe", "disabled": True}, _animal_options()))
    assert not any("onChange" in str(w.message) and "read-only" in str(w.message) for w in rec)


@pytest.mark.skipif(not is_dev(), reason="select DEV warnings")
def test_no_warn_when_on_change_present() -> None:
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        render_to_string(
            create_element("select", {"value": "giraffe", "onChange": lambda e: None}, _animal_options()),
        )
    assert not any("read-only" in str(w.message) for w in rec)


@pytest.mark.skipif(not is_dev(), reason="select DEV warnings")
def test_no_warn_uncontrolled_no_value_key() -> None:
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        render_to_string(create_element("select", None, _animal_options()))
    assert not any("read-only" in str(w.message) for w in rec)
