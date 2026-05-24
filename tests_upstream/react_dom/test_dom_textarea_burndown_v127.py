"""ReactDOMTextarea-test.js parity slice (v127): value, defaultValue, SSR, DEV warnings."""

from __future__ import annotations

import warnings
from typing import Any

import pytest
from ryact import create_element
from ryact.dev import is_dev
from ryact_dom.dom import Container, ElementNode
from ryact_dom.root import create_root
from ryact_dom.server import render_to_string


def _noop(_e: object) -> None:
    return None


def _host(c: Container) -> ElementNode:
    h = c.root.children[0]
    assert isinstance(h, ElementNode)
    return h


def _read_only_warn(msgs: list[str]) -> bool:
    return any(
        "provided a `value` prop" in m and "without an `onChange` handler" in m and "textarea" in m
        for m in msgs
    )


def _value_defaultvalue_warn(msgs: list[str]) -> bool:
    return any("both value and defaultValue props" in m and "textarea" in m for m in msgs)


def _null_value_warn(msgs: list[str]) -> bool:
    return any("`value` prop on `textarea` should not be null" in m for m in msgs)


def _invalid_value_warn(msgs: list[str]) -> bool:
    return any("Invalid value for prop `value` on <textarea>" in m for m in msgs)


def _children_warn(msgs: list[str]) -> bool:
    return any("Use the `defaultValue` or `value` props instead of setting children" in m for m in msgs)


class Symbol:  # noqa: A001 — parity with JS Symbol for inventory mapping
    pass


class ObjToString:
    def __init__(self, s: str) -> None:
        self._s = s

    def __str__(self) -> str:
        return self._s


class TemporalLike:
    def valueOf(self) -> object:
        raise TypeError("prod message")

    def __str__(self) -> str:
        return "2020-01-01"


# --- defaultValue / value display ---


def test_should_allow_setting_defaultvalue_3ff6093a() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("textarea", {"defaultValue": "giraffe"}))
    host = _host(c)
    assert host.dom_textarea_value() == "giraffe"
    r.render(create_element("textarea", {"defaultValue": "gorilla"}))
    assert host.dom_textarea_value() == "giraffe"
    host.value = "cat"
    r.render(create_element("textarea", {"defaultValue": "monkey"}))
    assert host.dom_textarea_value() == "cat"


def test_should_display_defaultvalue_of_number_0_422bf08b() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("textarea", {"defaultValue": 0}))
    assert _host(c).dom_textarea_value() == "0"


def test_should_display_defaultvalue_of_bigint_0_a58435b2() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("textarea", {"defaultValue": 0}))
    assert _host(c).dom_textarea_value() == "0"


def test_should_display_false_for_defaultvalue_of_false_b122f1fd() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("textarea", {"defaultValue": False}))
    assert _host(c).dom_textarea_value() == "false"


def test_should_display_foobar_for_defaultvalue_of_objtostring_99a51a06() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("textarea", {"defaultValue": ObjToString("foobar")}))
    assert _host(c).dom_textarea_value() == "foobar"


def test_should_set_defaultvalue_2c75e048() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("textarea", {"defaultValue": "foo"}))
    r.render(create_element("textarea", {"defaultValue": "bar"}))
    r.render(create_element("textarea", {"defaultValue": "noise"}))
    assert _host(c).default_value == "noise"


def test_should_not_render_value_as_an_attribute_7068f6dd() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("textarea", {"value": "giraffe", "onChange": _noop}))
    assert _host(c).get_attribute("value") is None
    assert "value" not in _host(c).props


def test_should_display_value_of_number_0_183c8022() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("textarea", {"value": 0, "onChange": _noop}))
    assert _host(c).dom_textarea_value() == "0"


def test_should_update_defaultvalue_to_empty_string_f33ca525() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("textarea", {"defaultValue": "foo"}))
    r.render(create_element("textarea", {"defaultValue": ""}))
    assert _host(c).default_value == ""


def test_should_allow_setting_value_to_giraffe_7dff50df() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("textarea", {"value": "giraffe", "onChange": _noop}))
    host = _host(c)
    assert host.dom_textarea_value() == "giraffe"
    r.render(create_element("textarea", {"value": "gorilla", "onChange": _noop}))
    assert host.dom_textarea_value() == "gorilla"


def test_will_not_initially_assign_empty_value_111a68a7() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("textarea", {"value": "", "readOnly": True}))
    host = _host(c)
    assert host.dom_textarea_value() == ""
    assert not host.children


def test_should_render_defaultvalue_for_ssr_b48b9c14() -> None:
    html = render_to_string(create_element("textarea", {"defaultValue": "1"}))
    assert "<textarea>1</textarea>" in html.replace(" ", "")
    assert "defaultvalue" not in html.lower()


def test_should_render_value_for_ssr_81dc71ad() -> None:
    html = render_to_string(create_element("textarea", {"value": "1", "onChange": _noop}))
    assert "<textarea>1</textarea>" in html.replace(" ", "")
    assert "defaultvalue" not in html.lower()


def test_should_allow_setting_value_to_true_b923f3a4() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("textarea", {"value": "giraffe", "onChange": _noop}))
    r.render(create_element("textarea", {"value": True, "onChange": _noop}))
    assert _host(c).dom_textarea_value() == "true"


def test_should_allow_setting_value_to_false_b23212af() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("textarea", {"value": "giraffe", "onChange": _noop}))
    r.render(create_element("textarea", {"value": False, "onChange": _noop}))
    assert _host(c).dom_textarea_value() == "false"


def test_should_allow_setting_value_to_objtostring_f4e664c1() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("textarea", {"value": "giraffe", "onChange": _noop}))
    r.render(create_element("textarea", {"value": ObjToString("foo"), "onChange": _noop}))
    assert _host(c).dom_textarea_value() == "foo"


def test_should_throw_when_value_is_set_to_a_temporal_like_object_4303304a() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("textarea", {"value": "giraffe", "onChange": _noop}))
    with pytest.raises(TypeError, match="prod message"):
        if is_dev():
            with warnings.catch_warnings(record=True):
                warnings.simplefilter("always")
                r.render(create_element("textarea", {"value": TemporalLike(), "onChange": _noop}))
        else:
            r.render(create_element("textarea", {"value": TemporalLike(), "onChange": _noop}))


def test_should_take_updates_to_defaultvalue_for_uncontrolled_textarea_cb15f0fc() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("textarea", {"defaultValue": "0"}))
    host = _host(c)
    assert host.dom_textarea_value() == "0"
    r.render(create_element("textarea", {"defaultValue": "1"}))
    assert host.dom_textarea_value() == "0"


def test_should_take_updates_to_children_in_lieu_of_defaultvalue_126aa148() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("textarea", {"defaultValue": "0"}))
    host = _host(c)
    assert host.dom_textarea_value() == "0"
    r.render(create_element("textarea", {}, "1"))
    assert host.dom_textarea_value() == "0"


def test_should_not_incur_unnecessary_dom_mutations_d1817f16() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("textarea", {"value": "a", "onChange": _noop}))
    c.ops.clear()
    r.render(create_element("textarea", {"value": "a", "onChange": _noop}))
    assert not any(op["op"] == "text" for op in c.ops)
    c.ops.clear()
    r.render(create_element("textarea", {"value": "b", "onChange": _noop}))
    assert any(op["op"] == "text" for op in c.ops)


def test_should_properly_control_a_value_of_number_0_c25c2625() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("textarea", {"value": 0, "onChange": _noop}))
    host = _host(c)
    host.value = "giraffe"
    host.dispatch_event("input")
    r.render(create_element("textarea", {"value": 0, "onChange": _noop}))
    assert host.dom_textarea_value() == "0"


def test_should_keep_value_when_switching_to_uncontrolled_if_not_changed_93bf2885() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("textarea", {"value": "kitten", "onChange": _noop}))
    host = _host(c)
    r.render(create_element("textarea", {"value": "puppies", "onChange": _noop}))
    assert host.dom_textarea_value() == "puppies"
    r.render(create_element("textarea", {"defaultValue": "gorilla"}))
    assert host.dom_textarea_value() == "puppies"


def test_should_keep_value_when_switching_to_uncontrolled_if_changed_79ff7f44() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("textarea", {"value": "kitten", "onChange": _noop}))
    host = _host(c)
    r.render(create_element("textarea", {"defaultValue": "gorilla"}))
    assert host.dom_textarea_value() == "kitten"


def test_should_unmount_8f06ef9c() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("textarea", {}))
    r.unmount()


@pytest.mark.skipif(not is_dev(), reason="textarea DEV warnings")
def test_should_warn_if_value_is_null_4ae769af() -> None:
    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("textarea", {"value": None}))
    assert _null_value_warn([str(w.message) for w in rec])
    with warnings.catch_warnings(record=True) as rec2:
        warnings.simplefilter("always")
        r.render(create_element("textarea", {"value": None}))
    assert _null_value_warn([str(w.message) for w in rec2])


@pytest.mark.skipif(not is_dev(), reason="textarea DEV warnings")
def test_should_warn_if_value_and_defaultvalue_are_specified_fb16a8af() -> None:
    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(
            create_element(
                "textarea",
                {"value": "foo", "defaultValue": "bar", "readOnly": True},
            )
        )
    assert _value_defaultvalue_warn([str(w.message) for w in rec])


def test_should_not_warn_about_missing_onchange_in_uncontrolled_textareas_894b0b7b() -> None:
    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("textarea", {}))
    assert not _read_only_warn([str(w.message) for w in rec])
    r.unmount()
    r2 = create_root(c)
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        r2.render(create_element("textarea", {}))


def test_does_not_set_textcontent_if_value_is_unchanged_22f93193() -> None:
    def parent(count: int) -> Any:
        return create_element(
            "div",
            {},
            create_element("span", {"key": "s"}, str(count)),
            create_element(
                "textarea",
                {"key": "t", "value": "foo", "onChange": _noop, "data-count": count},
            ),
        )

    c = Container()
    r = create_root(c)
    r.render(parent(0))
    c.ops.clear()
    r.render(parent(1))
    assert not any(op["op"] == "text" and op.get("path") == [0, 1, 0] for op in c.ops)


# --- Symbol / function values ---


@pytest.mark.skipif(not is_dev(), reason="invalid value DEV warnings")
def test_treats_initial_symbol_value_as_empty_47d8ce96() -> None:
    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("textarea", {"value": Symbol(), "onChange": _noop}))
    assert _invalid_value_warn([str(w.message) for w in rec])
    assert _host(c).dom_textarea_value() == ""


@pytest.mark.skipif(not is_dev(), reason="textarea children DEV warnings")
def test_treats_initial_symbol_children_as_empty_e561a9fa() -> None:
    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("textarea", {"onChange": _noop}, Symbol()))
    assert _children_warn([str(w.message) for w in rec])
    assert _host(c).dom_textarea_value() == ""


@pytest.mark.skipif(not is_dev(), reason="invalid value DEV warnings")
def test_treats_updated_symbol_value_as_empty_e8fba000() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("textarea", {"value": "foo", "onChange": _noop}))
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("textarea", {"value": Symbol(), "onChange": _noop}))
    assert _invalid_value_warn([str(w.message) for w in rec])
    assert _host(c).dom_textarea_value() == ""


def test_treats_initial_symbol_defaultvalue_as_empty_e92bd359() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("textarea", {"defaultValue": Symbol()}))
    assert _host(c).dom_textarea_value() == ""


def test_treats_updated_symbol_defaultvalue_as_empty_38c2c5da() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("textarea", {"defaultValue": "foo"}))
    r.render(create_element("textarea", {"defaultValue": Symbol()}))
    assert _host(c).dom_textarea_value() == "foo"


@pytest.mark.skipif(not is_dev(), reason="invalid value DEV warnings")
def test_treats_initial_function_value_as_empty_68eb9818() -> None:
    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("textarea", {"value": _noop, "onChange": _noop}))
    assert _invalid_value_warn([str(w.message) for w in rec])
    assert _host(c).dom_textarea_value() == ""


@pytest.mark.skipif(not is_dev(), reason="textarea children DEV warnings")
def test_treats_initial_function_children_as_empty_dbe6777d() -> None:
    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("textarea", {"onChange": _noop}, _noop))
    assert _children_warn([str(w.message) for w in rec])
    assert _host(c).dom_textarea_value() == ""


@pytest.mark.skipif(not is_dev(), reason="invalid value DEV warnings")
def test_treats_updated_function_value_as_empty_0402cf11() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("textarea", {"value": "foo", "onChange": _noop}))
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("textarea", {"value": _noop, "onChange": _noop}))
    assert _invalid_value_warn([str(w.message) for w in rec])
    assert _host(c).dom_textarea_value() == ""


def test_treats_initial_function_defaultvalue_as_empty_aeb50684() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("textarea", {"defaultValue": _noop}))
    assert _host(c).dom_textarea_value() == ""


def test_treats_updated_function_defaultvalue_as_empty_33eb783a() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("textarea", {"defaultValue": "foo"}))
    r.render(create_element("textarea", {"defaultValue": _noop}))
    assert _host(c).dom_textarea_value() == "foo"


def test_should_remove_previous_defaultvalue_349dde6c() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("textarea", {"defaultValue": "0"}))
    host = _host(c)
    assert host.dom_textarea_value() == "0"
    assert host.default_value == "0"
    r.render(create_element("textarea", {}))
    assert host.default_value == ""


def test_should_treat_defaultvalue_null_as_missing_a6ae614c() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("textarea", {"defaultValue": "0"}))
    host = _host(c)
    r.render(create_element("textarea", {"defaultValue": None}))
    assert host.default_value == ""


def test_should_not_warn_about_missing_onchange_if_value_is_undefined_ea8d17c0() -> None:
    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("textarea", {}))
    assert not _read_only_warn([str(w.message) for w in rec])


def test_should_not_warn_about_missing_onchange_if_onchange_is_set_0bbcb61d() -> None:
    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("textarea", {"value": "something", "onChange": _noop}))
    assert not _read_only_warn([str(w.message) for w in rec])


def test_should_not_warn_about_missing_onchange_if_disabled_is_true_57c11b1d() -> None:
    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("textarea", {"value": "something", "disabled": True}))
    assert not _read_only_warn([str(w.message) for w in rec])


def test_should_not_warn_about_missing_onchange_if_value_is_not_set_57386928() -> None:
    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("textarea", {"value": "something", "readOnly": True}))
    assert not _read_only_warn([str(w.message) for w in rec])


@pytest.mark.skipif(not is_dev(), reason="read-only controlled textarea DEV warnings")
def test_should_warn_about_missing_onchange_if_value_is_false_6c7fc0eb() -> None:
    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("textarea", {"value": False}))
    assert _read_only_warn([str(w.message) for w in rec])


@pytest.mark.skipif(not is_dev(), reason="read-only controlled textarea DEV warnings")
def test_should_warn_about_missing_onchange_if_value_is_0_02a9b496() -> None:
    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("textarea", {"value": 0}))
    assert _read_only_warn([str(w.message) for w in rec])


@pytest.mark.skipif(not is_dev(), reason="read-only controlled textarea DEV warnings")
def test_should_warn_about_missing_onchange_if_value_is_0_string_9724601b() -> None:
    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("textarea", {"value": "0"}))
    assert _read_only_warn([str(w.message) for w in rec])


@pytest.mark.skipif(not is_dev(), reason="read-only controlled textarea DEV warnings")
def test_should_warn_about_missing_onchange_if_value_is_empty_4e39e59e() -> None:
    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("textarea", {"value": ""}))
    assert _read_only_warn([str(w.message) for w in rec])
