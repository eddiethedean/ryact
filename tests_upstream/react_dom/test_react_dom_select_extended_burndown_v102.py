# Translated subset: ReactDOMSelect-test.js — invalid option values + Temporal-like coercion
from __future__ import annotations

import warnings
from collections.abc import Iterator
from contextlib import suppress
from typing import Any

import pytest
from ryact import create_element
from ryact.dev import is_dev
from ryact.element import UNDEFINED
from ryact_dom.dom import Container, ElementNode, TextNode
from ryact_dom.root import create_root
from ryact_dom.select_binding import _invalid_option_host_value
from ryact_dom.server import render_to_string


@pytest.fixture(autouse=True)
def _dev_only_guards() -> Iterator[None]:
    yield


class Symbol:  # noqa: A001 — parity with JS Symbol for inventory mapping
    pass


class TemporalLike:
    def __str__(self) -> str:
        raise TypeError("prod message")


def _label_from_dom_option(node: ElementNode) -> str:
    parts: list[str] = []
    for c in node.children:
        if isinstance(c, TextNode):
            parts.append(c.text)
    return "".join(parts)


def _dom_value_shows_label(v: Any) -> bool:
    return bool(v is not None and _invalid_option_host_value(v))


def _select_dom_value(container: Container) -> str:
    sel = container.root.children[0]
    assert isinstance(sel, ElementNode)
    assert sel.tag.lower() == "select"
    for ch in sel.children:
        if isinstance(ch, ElementNode) and ch.tag.lower() == "option" and ch.props.get("selected"):
            v = ch.props.get("value")
            if _dom_value_shows_label(v):
                return _label_from_dom_option(ch)
            if v is None and ch.children and isinstance(ch.children[0], TextNode):
                v = ch.children[0].text
            return "" if v is None else str(v)
    return ""


def _animal_options_fn_sym(callable_val):
    return (
        create_element("option", {"value": callable_val}, "A function!" if callable(callable_val) else "A Symbol!"),
        create_element("option", {"value": "monkey"}, "A monkey!"),
        create_element("option", {"value": "giraffe"}, "A giraffe!"),
    )


def test_function_initial_value_uses_option_label() -> None:
    c = Container()
    root = create_root(c)
    fn = lambda: None  # noqa: E731
    if is_dev():
        with warnings.catch_warnings(record=True) as rec:
            warnings.simplefilter("always")
            root.render(create_element("select", {"value": fn, "onChange": lambda e: None}, _animal_options_fn_sym(fn)))
        assert any("Invalid value for prop `value` on tag" in str(w.message) for w in rec)
    else:
        root.render(create_element("select", {"value": fn, "onChange": lambda e: None}, _animal_options_fn_sym(fn)))
    assert _select_dom_value(c) == "A function!"


def test_function_initial_default_value_uses_option_label() -> None:
    c = Container()
    root = create_root(c)
    fn = lambda: None  # noqa: E731
    if is_dev():
        with warnings.catch_warnings(record=True) as rec:
            warnings.simplefilter("always")
            root.render(create_element("select", {"defaultValue": "A function!"}, _animal_options_fn_sym(fn)))
        assert any("Invalid value for prop `value` on tag" in str(w.message) for w in rec)
    else:
        root.render(create_element("select", {"defaultValue": "A function!"}, _animal_options_fn_sym(fn)))
    assert _select_dom_value(c) == "A function!"


def test_function_value_updates_resync() -> None:
    c = Container()
    root = create_root(c)
    fn = lambda: None  # noqa: E731
    if is_dev():
        with warnings.catch_warnings(record=True) as rec:
            warnings.simplefilter("always")
            root.render(
                create_element("select", {"value": "monkey", "onChange": lambda e: None}, _animal_options_fn_sym(fn)),
            )
        assert any("Invalid value for prop `value` on tag" in str(w.message) for w in rec)
    else:
        root.render(
            create_element("select", {"value": "monkey", "onChange": lambda e: None}, _animal_options_fn_sym(fn))
        )
    assert _select_dom_value(c) == "monkey"
    if is_dev():
        with warnings.catch_warnings(record=True) as rec:
            warnings.simplefilter("always")
            root.render(create_element("select", {"value": fn, "onChange": lambda e: None}, _animal_options_fn_sym(fn)))
        assert any("Invalid value for prop `value` on tag" in str(w.message) for w in rec)
    else:
        root.render(create_element("select", {"value": fn, "onChange": lambda e: None}, _animal_options_fn_sym(fn)))
    assert _select_dom_value(c) == "A function!"


def test_function_default_value_update_second_container() -> None:
    c1 = Container()
    r1 = create_root(c1)
    fn = lambda: None  # noqa: E731
    if is_dev():
        with warnings.catch_warnings(record=True) as rec:
            warnings.simplefilter("always")
            r1.render(create_element("select", None, _animal_options_fn_sym(fn)))
        assert any("Invalid value for prop `value` on tag" in str(w.message) for w in rec)
    else:
        r1.render(create_element("select", None, _animal_options_fn_sym(fn)))
    assert _select_dom_value(c1) == "monkey"
    c2 = Container()
    r2 = create_root(c2)
    if is_dev():
        with warnings.catch_warnings(record=True) as rec:
            warnings.simplefilter("always")
            r2.render(create_element("select", {"defaultValue": "A function!"}, _animal_options_fn_sym(fn)))
        assert any("Invalid value for prop `value` on tag" in str(w.message) for w in rec)
    else:
        r2.render(create_element("select", {"defaultValue": "A function!"}, _animal_options_fn_sym(fn)))
    assert _select_dom_value(c2) == "A function!"


def test_symbol_initial_value_uses_option_label() -> None:
    c = Container()
    root = create_root(c)
    sym = Symbol()
    if is_dev():
        with warnings.catch_warnings(record=True) as rec:
            warnings.simplefilter("always")
            root.render(
                create_element("select", {"value": sym, "onChange": lambda e: None}, _animal_options_fn_sym(sym))
            )
        assert any("Invalid value for prop `value` on tag" in str(w.message) for w in rec)
    else:
        root.render(create_element("select", {"value": sym, "onChange": lambda e: None}, _animal_options_fn_sym(sym)))
    assert _select_dom_value(c) == "A Symbol!"


def test_symbol_initial_default_value_uses_option_label() -> None:
    c = Container()
    root = create_root(c)
    sym = Symbol()
    if is_dev():
        with warnings.catch_warnings(record=True) as rec:
            warnings.simplefilter("always")
            root.render(create_element("select", {"defaultValue": "A Symbol!"}, _animal_options_fn_sym(sym)))
        assert any("Invalid value for prop `value` on tag" in str(w.message) for w in rec)
    else:
        root.render(create_element("select", {"defaultValue": "A Symbol!"}, _animal_options_fn_sym(sym)))
    assert _select_dom_value(c) == "A Symbol!"


def test_symbol_value_updates_resync() -> None:
    c = Container()
    root = create_root(c)
    sym = Symbol()
    if is_dev():
        with warnings.catch_warnings(record=True) as rec:
            warnings.simplefilter("always")
            root.render(
                create_element("select", {"value": "monkey", "onChange": lambda e: None}, _animal_options_fn_sym(sym)),
            )
        assert any("Invalid value for prop `value` on tag" in str(w.message) for w in rec)
    else:
        root.render(
            create_element("select", {"value": "monkey", "onChange": lambda e: None}, _animal_options_fn_sym(sym))
        )
    assert _select_dom_value(c) == "monkey"
    if is_dev():
        with warnings.catch_warnings(record=True) as rec:
            warnings.simplefilter("always")
            root.render(
                create_element("select", {"value": sym, "onChange": lambda e: None}, _animal_options_fn_sym(sym))
            )
        assert any("Invalid value for prop `value` on tag" in str(w.message) for w in rec)
    else:
        root.render(create_element("select", {"value": sym, "onChange": lambda e: None}, _animal_options_fn_sym(sym)))
    assert _select_dom_value(c) == "A Symbol!"


def test_symbol_default_value_update_second_container() -> None:
    c1 = Container()
    r1 = create_root(c1)
    sym = Symbol()
    if is_dev():
        with warnings.catch_warnings(record=True) as rec:
            warnings.simplefilter("always")
            r1.render(create_element("select", None, _animal_options_fn_sym(sym)))
        assert any("Invalid value for prop `value` on tag" in str(w.message) for w in rec)
    else:
        r1.render(create_element("select", None, _animal_options_fn_sym(sym)))
    assert _select_dom_value(c1) == "monkey"
    c2 = Container()
    r2 = create_root(c2)
    if is_dev():
        with warnings.catch_warnings(record=True) as rec:
            warnings.simplefilter("always")
            r2.render(create_element("select", {"defaultValue": "A Symbol!"}, _animal_options_fn_sym(sym)))
        assert any("Invalid value for prop `value` on tag" in str(w.message) for w in rec)
    else:
        r2.render(create_element("select", {"defaultValue": "A Symbol!"}, _animal_options_fn_sym(sym)))
    assert _select_dom_value(c2) == "A Symbol!"


@pytest.mark.skipif(not is_dev(), reason="select DEV warnings")
def test_explicit_undefined_value_no_readonly_warning() -> None:
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        render_to_string(
            create_element(
                "select",
                {"value": UNDEFINED},
                create_element("option", {"value": "monkey"}, "A monkey!"),
                create_element("option", {"value": "giraffe"}, "A giraffe!"),
                create_element("option", {"value": "gorilla"}, "A gorilla!"),
            ),
        )
    assert not any("read-only" in str(w.message) for w in rec)


def _opts_temporal(*, opt_bad: bool = False, opt_text: str = "2020-01-01"):
    return (
        create_element(
            "option",
            {"value": TemporalLike() if opt_bad else opt_text},
            "like a Temporal.PlainDate",
        ),
        create_element("option", {"value": "monkey"}, "A monkey!"),
        create_element("option", {"value": "giraffe"}, "A giraffe!"),
    )


def test_temporal_select_value_throws() -> None:
    with pytest.raises(TypeError, match="prod message"):
        render_to_string(
            create_element(
                "select",
                {"value": TemporalLike(), "onChange": lambda e: None},
                _opts_temporal(),
            ),
        )


@pytest.mark.skipif(not is_dev(), reason="temporal DEV warnings")
def test_temporal_select_value_dev_warnings() -> None:
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        with suppress(TypeError):
            render_to_string(
                create_element(
                    "select",
                    {"value": TemporalLike(), "onChange": lambda e: None},
                    _opts_temporal(),
                ),
            )
    assert any("must be strings, not TemporalLike" in str(w.message) for w in rec)


def test_temporal_option_value_throws() -> None:
    with pytest.raises(TypeError, match="prod message"):
        render_to_string(
            create_element(
                "select",
                {"value": "2020-01-01", "onChange": lambda e: None},
                _opts_temporal(opt_bad=True),
            ),
        )


@pytest.mark.skipif(not is_dev(), reason="temporal DEV warnings")
def test_temporal_option_value_dev_warnings() -> None:
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        with suppress(TypeError):
            render_to_string(
                create_element(
                    "select",
                    {"value": "2020-01-01", "onChange": lambda e: None},
                    _opts_temporal(opt_bad=True),
                ),
            )
    assert any("unsupported type TemporalLike" in str(w.message) for w in rec)


def test_temporal_both_value_throws_from_option_first() -> None:
    with pytest.raises(TypeError, match="prod message"):
        render_to_string(
            create_element(
                "select",
                {"value": TemporalLike(), "onChange": lambda e: None},
                _opts_temporal(opt_bad=True),
            ),
        )


def test_temporal_default_value_select_throws() -> None:
    if is_dev():
        with warnings.catch_warnings(record=True) as rec:
            warnings.simplefilter("always")
            with pytest.raises(TypeError, match="prod message"):
                render_to_string(
                    create_element(
                        "select",
                        {"defaultValue": TemporalLike(), "onChange": lambda e: None},
                        _opts_temporal(),
                    ),
                )
        assert any("must be strings, not TemporalLike" in str(w.message) for w in rec)
    else:
        with pytest.raises(TypeError, match="prod message"):
            render_to_string(
                create_element(
                    "select",
                    {"defaultValue": TemporalLike(), "onChange": lambda e: None},
                    _opts_temporal(),
                ),
            )


def test_temporal_default_value_option_throws() -> None:
    with pytest.raises(TypeError, match="prod message"):
        render_to_string(
            create_element(
                "select",
                {"defaultValue": "2020-01-01", "onChange": lambda e: None},
                _opts_temporal(opt_bad=True),
            ),
        )


def test_temporal_default_value_both_throws() -> None:
    with pytest.raises(TypeError, match="prod message"):
        render_to_string(
            create_element(
                "select",
                {"defaultValue": TemporalLike(), "onChange": lambda e: None},
                _opts_temporal(opt_bad=True),
            ),
        )


def test_temporal_updated_select_value_throws() -> None:
    c = Container()
    root = create_root(c)
    root.render(
        create_element(
            "select",
            {"value": "monkey", "onChange": lambda e: None},
            _opts_temporal(),
        ),
    )
    assert _select_dom_value(c) == "monkey"
    with pytest.raises(TypeError, match="prod message"):
        root.render(
            create_element(
                "select",
                {"value": TemporalLike(), "onChange": lambda e: None},
                _opts_temporal(),
            ),
        )


def test_temporal_updated_option_value_throws() -> None:
    c = Container()
    root = create_root(c)
    root.render(
        create_element(
            "select",
            {"value": "2020-01-01", "onChange": lambda e: None},
            create_element("option", {"value": "donkey"}, "like a Temporal.PlainDate"),
            create_element("option", {"value": "monkey"}, "A monkey!"),
            create_element("option", {"value": "giraffe"}, "A giraffe!"),
        ),
    )
    with pytest.raises(TypeError, match="prod message"):
        root.render(
            create_element(
                "select",
                {"value": "2020-01-01", "onChange": lambda e: None},
                _opts_temporal(opt_bad=True),
            ),
        )


def test_temporal_updated_value_both_throws() -> None:
    c = Container()
    root = create_root(c)
    root.render(
        create_element(
            "select",
            {"value": "donkey", "onChange": lambda e: None},
            create_element("option", {"value": "donkey"}, "like a Temporal.PlainDate"),
            create_element("option", {"value": "monkey"}, "A monkey!"),
            create_element("option", {"value": "giraffe"}, "A giraffe!"),
        ),
    )
    with pytest.raises(TypeError, match="prod message"):
        root.render(
            create_element(
                "select",
                {"value": TemporalLike(), "onChange": lambda e: None},
                _opts_temporal(opt_bad=True),
            ),
        )


def test_temporal_updated_default_value_select_throws() -> None:
    c = Container()
    root = create_root(c)
    root.render(
        create_element(
            "select",
            {"defaultValue": "monkey", "onChange": lambda e: None},
            _opts_temporal(),
        ),
    )
    with pytest.raises(TypeError, match="prod message"):
        root.render(
            create_element(
                "select",
                {"defaultValue": TemporalLike(), "onChange": lambda e: None},
                _opts_temporal(),
            ),
        )


def test_temporal_updated_default_value_both_throws() -> None:
    c = Container()
    root = create_root(c)
    root.render(
        create_element(
            "select",
            {"defaultValue": "monkey", "onChange": lambda e: None},
            create_element("option", {"value": "donkey"}, "like a Temporal.PlainDate"),
            create_element("option", {"value": "monkey"}, "A monkey!"),
            create_element("option", {"value": "giraffe"}, "A giraffe!"),
        ),
    )
    with pytest.raises(TypeError, match="prod message"):
        root.render(
            create_element(
                "select",
                {"value": TemporalLike(), "onChange": lambda e: None},
                _opts_temporal(opt_bad=True),
            ),
        )
