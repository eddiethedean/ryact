"""ReactDOMInput-test.js parity: value/checked attrs, radio, events, reset, hydrate (v133)."""

from __future__ import annotations

import warnings
from typing import Any

import pytest
from ryact import Component, create_element, use_state
from ryact.dev import is_dev
from ryact_dom.dom import Container, ElementNode, SyntheticEvent
from ryact_dom.input_host import assert_input_tracking_is_current, is_checked_dirty, is_value_dirty
from ryact_dom.root import create_root, hydrate_root


def _noop(_e: object) -> None:
    return None


def _host(c: Container) -> ElementNode:
    h = c.root.children[0]
    assert isinstance(h, ElementNode)
    return h


def _inputs(c: Container) -> list[ElementNode]:
    return [n for n in c.query_selector_all("input") if isinstance(n, ElementNode)]


def _controlled_number_input(**props: Any) -> object:
    initial = props.get("value", 1)
    value, set_value = use_state(initial)
    t = props.get("type", "number")
    return create_element(
        "input",
        {"type": t, "value": value, "onChange": lambda e: set_value(e.target.value)},
    )


def test_changes_the_number_2_to_20_using_a_change_handler_2de58a80() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element(_controlled_number_input, {"value": 2}))
    node = _host(c)
    node.set_untracked_value("2.0")
    node.dispatch_event("input")
    r.render(create_element(_controlled_number_input, {"value": 2}))
    assert node.value == "2.0"
    assert node.get_attribute("value") == "2.0"


def test_always_sets_the_attribute_when_values_change_on_text_inputs_7f885871() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element(_controlled_number_input, {"value": 1, "type": "text"}))
    node = _host(c)
    assert is_value_dirty(node) is False
    node.set_untracked_value("2")
    node.dispatch_event("input")
    assert is_value_dirty(node) is True
    assert node.get_attribute("value") == "2"


def test_does_not_set_the_value_attribute_on_number_inputs_if_focused_54433d4f() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "number", "value": 1, "onChange": _noop}))
    node = _host(c)
    assert is_value_dirty(node) is True
    node.focus()
    node.set_untracked_value("2")
    node.dispatch_event("input")
    assert node.get_attribute("value") == "1"


def test_sets_the_value_attribute_on_number_inputs_on_blur_38bde914() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element(_controlled_number_input, {"value": 1}))
    node = _host(c)
    node.focus()
    node.set_untracked_value("2")
    node.dispatch_event("input")
    node.blur()
    assert node.value == "2"
    assert node.get_attribute("value") == "2"


def test_an_uncontrolled_number_input_will_not_update_the_value_attribute_on_blur_6dd1e14e() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "number", "defaultValue": 1}))
    node = _host(c)
    assert is_value_dirty(node) is True
    node.focus()
    node.set_untracked_value(4)
    node.dispatch_event("input")
    node.blur()
    assert node.get_attribute("value") == "1"


def test_an_uncontrolled_text_input_will_not_update_the_value_attribute_on_blur_5522b7f2() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "text", "defaultValue": 1}))
    node = _host(c)
    assert is_value_dirty(node) is True
    node.focus()
    node.set_untracked_value(4)
    node.dispatch_event("input")
    node.blur()
    assert node.get_attribute("value") == "1"


def test_resets_value_of_datetime_input_to_fix_bugs_in_ios_safari_1a4813a6() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "date", "defaultValue": "1980-01-01"}))
    node = _host(c)
    assert node._input_mount_log == ["type", "value", "defaultValue"]


def test_should_have_the_correct_target_value_6d7bb192() -> None:
    handled = False

    def handler(event: SyntheticEvent) -> None:
        nonlocal handled
        assert event.target.tag == "input"
        handled = True

    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "text", "onInput": handler}))
    node = _host(c)
    node.set_untracked_value("giraffe")
    node.dispatch_event("input")
    assert handled


def test_should_have_a_this_value_of_undefined_if_bind_is_not_used_59d64b64() -> None:
    seen: list[str] = []

    def unbound_input_on_change(_: SyntheticEvent) -> None:
        seen.append("ok")

    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "text", "onInput": unbound_input_on_change}))
    node = _host(c)
    node.set_untracked_value("giraffe")
    node.dispatch_event("input")
    assert seen == ["ok"]


def test_should_notice_input_changes_when_reverting_back_to_original_value_344da512() -> None:
    log: list[str] = []

    def on_change(e: SyntheticEvent) -> None:
        log.append(e.target.value)

    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "text", "value": "a", "onChange": on_change}))
    r.render(create_element("input", {"type": "text", "value": "a", "onChange": on_change}))
    node = _host(c)
    node.set_untracked_value("")
    node.dispatch_event("input")
    assert log == [""]
    assert node.value == "a"


@pytest.mark.skipif(not is_dev(), reason="controlled input DEV warnings")
def test_should_remove_the_value_attribute_on_reset_inputs_when_value_updated_to_undefined_f6d725ca() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "reset", "value": "banana", "onChange": _noop}))
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        r.render(create_element("input", {"type": "reset", "onChange": _noop}))
    node = _host(c)
    assert node.get_attribute("value") is None


@pytest.mark.skipif(not is_dev(), reason="controlled input DEV warnings")
def test_should_remove_the_value_attribute_on_submit_inputs_when_value_updated_to_undefined_42936f1d() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "submit", "value": "banana", "onChange": _noop}))
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        r.render(create_element("input", {"type": "submit", "onChange": _noop}))
    node = _host(c)
    assert node.get_attribute("value") is None


def test_should_restore_uncontrolled_inputs_to_last_defaultvalue_upon_reset_a0555034() -> None:
    c = Container()
    r = create_root(c)
    r.render(
        create_element(
            "form",
            None,
            create_element("input", {"defaultValue": "default1"}),
        )
    )
    form = c.root.children[0]
    assert isinstance(form, ElementNode)
    inp = form.children[0]
    assert isinstance(inp, ElementNode)
    assert inp.value == "default1"
    assert is_value_dirty(inp) is True
    inp.set_untracked_value("changed")
    inp.dispatch_event("input")
    assert inp.value == "changed"
    r.render(
        create_element(
            "form",
            None,
            create_element("input", {"defaultValue": "default2"}),
        )
    )
    inp = form.children[0]
    assert isinstance(inp, ElementNode)
    assert inp.value == "changed"
    form = c.root.children[0]
    assert isinstance(form, ElementNode)
    form.reset()
    inp = form.children[0]
    assert isinstance(inp, ElementNode)
    assert inp.value == "default2"
    assert is_value_dirty(inp) is False


def _radio_nodes_from_two_form_wrapper(c: Container) -> tuple[ElementNode, ElementNode, ElementNode]:
    wrapper = c.root.children[0]
    assert isinstance(wrapper, ElementNode)
    forms = [ch for ch in wrapper.children if isinstance(ch, ElementNode) and ch.tag == "form"]
    assert len(forms) == 2
    a = forms[0].children[0]
    b = forms[0].children[1]
    cc = forms[1].children[0]
    assert isinstance(a, ElementNode) and isinstance(b, ElementNode) and isinstance(cc, ElementNode)
    return a, b, cc


def test_should_control_radio_buttons_c13e3ec7() -> None:
    c = Container()
    r = create_root(c)
    r.render(
        create_element(
            "div",
            None,
            create_element(
                "form",
                None,
                create_element(
                    "input",
                    {"type": "radio", "name": "fruit", "checked": True, "onChange": _noop},
                ),
                create_element(
                    "input",
                    {"type": "radio", "name": "fruit", "onChange": _noop},
                ),
            ),
            create_element(
                "form",
                None,
                create_element(
                    "input",
                    {"type": "radio", "name": "fruit", "checked": True, "onChange": _noop},
                ),
            ),
        )
    )
    a, b, cc = _radio_nodes_from_two_form_wrapper(c)
    assert isinstance(a, ElementNode) and isinstance(b, ElementNode) and isinstance(cc, ElementNode)
    assert a.checked is True and b.checked is False and cc.checked is True
    assert a.has_attribute("checked") and not b.has_attribute("checked") and cc.has_attribute("checked")
    assert is_checked_dirty(a) and is_checked_dirty(b) and is_checked_dirty(cc)
    assert_input_tracking_is_current(c)
    b.set_untracked_checked(True)
    assert a.checked is False and cc.checked is True
    b.dispatch_event("click")
    assert a.checked is True and cc.checked is True


def test_shouldnt_get_tricked_by_changing_radio_names_part_2_eed5445e() -> None:
    c = Container()
    r = create_root(c)
    r.render(
        create_element(
            "div",
            None,
            create_element("input", {"type": "radio", "name": "a", "value": "1", "checked": True, "onChange": _noop}),
            create_element("input", {"type": "radio", "name": "a", "value": "2", "onChange": _noop}),
        )
    )
    one, two = _inputs(c)
    assert one.checked and not two.checked
    r.render(
        create_element(
            "div",
            None,
            create_element("input", {"type": "radio", "name": "b", "value": "1", "checked": True, "onChange": _noop}),
            create_element("input", {"type": "radio", "name": "b", "value": "2", "checked": True, "onChange": _noop}),
        )
    )
    one, two = _inputs(c)
    assert one.checked and two.checked
    assert_input_tracking_is_current(c)


def test_should_check_the_correct_radio_when_the_selected_name_moves_d5f74ef8() -> None:
    def radio_name_move() -> object:
        updated, set_updated = use_state(False)
        radio_name = "secondName" if updated else "firstName"
        return create_element(
            "div",
            None,
            create_element("button", {"type": "button", "onClick": lambda _: set_updated(not updated)}),
            create_element("input", {"type": "radio", "name": radio_name, "value": "one", "onChange": _noop}),
            create_element(
                "input",
                {"type": "radio", "name": radio_name, "value": "two", "checked": True, "onChange": _noop},
            ),
        )

    c = Container()
    r = create_root(c)
    r.render(create_element(radio_name_move, None))
    wrapper = _host(c)
    button = wrapper.children[0]
    radio_one = wrapper.children[1]
    radio_two = wrapper.children[2]
    assert isinstance(button, ElementNode) and isinstance(radio_one, ElementNode) and isinstance(radio_two, ElementNode)
    assert is_checked_dirty(radio_two)
    assert radio_one.checked is False and radio_two.checked is True
    button.dispatch_event("click")
    radio_two = wrapper.children[2]
    assert isinstance(radio_two, ElementNode)
    assert radio_two.checked is True
    button.dispatch_event("click")
    radio_two = wrapper.children[2]
    assert isinstance(radio_two, ElementNode)
    assert radio_two.checked is True


def test_should_control_a_value_in_reentrant_events_8703cfa8() -> None:
    switched = {"v": False}
    box: dict[str, Container] = {}

    def reentrant_app() -> object:
        value, set_value = use_state("lion")

        def change(new_value: str) -> None:
            set_value(new_value)
            container = box["c"]
            wrapper = container.root.children[0]
            assert isinstance(wrapper, ElementNode)
            b = wrapper.children[1]
            assert isinstance(b, ElementNode)
            b.focus()

        def blur_val(current_value: str) -> None:
            switched["v"] = True
            set_value(current_value)

        return create_element(
            "div",
            None,
            create_element(
                "input",
                {
                    "value": value,
                    "onChange": lambda e: change(e.target.value),
                    "onBlur": lambda e: blur_val(e.target.value),
                },
            ),
            create_element("input", None),
        )

    c = Container()
    box["c"] = c
    r = create_root(c)
    r.render(create_element(reentrant_app, None))
    wrapper = _host(c)
    a = wrapper.children[0]
    assert isinstance(a, ElementNode)
    a.focus()
    a.set_untracked_value("giraffe")
    a.dispatch_event("input")
    r.render(create_element(reentrant_app, None))
    a = wrapper.children[0]
    assert isinstance(a, ElementNode)
    a.dispatch_event("blur")
    a.dispatch_event("focusout")
    assert a.value == "giraffe"
    assert switched["v"] is True


def test_should_control_values_in_reentrant_events_with_different_targets_296285cd() -> None:
    box: dict[str, Container] = {}

    def reentrant_checkbox() -> object:
        def change() -> None:
            container = box["c"]
            wrapper = container.root.children[0]
            assert isinstance(wrapper, ElementNode)
            b = wrapper.children[1]
            assert isinstance(b, ElementNode)
            b.click()

        return create_element(
            "div",
            None,
            create_element("input", {"value": "lion", "onChange": lambda _e: change()}),
            create_element("input", {"type": "checkbox", "checked": True, "onChange": _noop}),
        )

    c = Container()
    box["c"] = c
    r = create_root(c)
    r.render(create_element(reentrant_checkbox, None))
    wrapper = _host(c)
    a, b = wrapper.children[0], wrapper.children[1]
    assert isinstance(a, ElementNode) and isinstance(b, ElementNode)
    a.set_untracked_value("giraffe")
    a.dispatch_event("input")
    assert a.value == "lion"
    assert b.checked is True


def test_should_control_radio_buttons_if_tree_updates_during_render_case_2_9dcf77f9() -> None:
    thunk: list[Any] = []

    def App() -> object:
        disabled, set_disabled = use_state(False)
        value, set_value = use_state("one")

        def handle_change(e: SyntheticEvent) -> None:
            set_disabled(True)

            def do_it() -> None:
                set_disabled(False)
                set_value(e.target.value)

            thunk.clear()
            thunk.append(do_it)

        return create_element(
            "div",
            None,
            create_element(
                "input",
                {
                    "type": "radio",
                    "name": "n",
                    "value": "one",
                    "checked": value == "one",
                    "disabled": disabled,
                    "onChange": handle_change,
                },
            ),
            create_element(
                "input",
                {
                    "type": "radio",
                    "name": "n",
                    "value": "two",
                    "checked": value == "two",
                    "disabled": disabled,
                    "onChange": handle_change,
                },
            ),
        )

    c = Container()
    r = create_root(c)
    r.render(create_element(App, None))
    one, two = _inputs(c)
    assert one.checked and not two.checked
    two.set_untracked_checked(True)
    two.dispatch_event("click")
    assert one.checked and not two.checked
    assert thunk
    thunk[0]()
    r.render(create_element(App, None))
    one, two = _inputs(c)
    assert not one.checked and two.checked
    one.set_untracked_checked(True)
    one.dispatch_event("click")
    assert not one.checked and two.checked
    thunk[0]()
    r.render(create_element(App, None))
    one, two = _inputs(c)
    assert one.checked and not two.checked


@pytest.mark.skipif(not is_dev(), reason="radio controlled DEV warnings")
def test_should_not_warn_if_radio_value_changes_but_never_becomes_controlled_b9d8c98a() -> None:
    c = Container()
    r = create_root(c)
    for props in (
        {"type": "radio", "value": "a"},
        {"type": "radio", "value": "b"},
        {"type": "radio"},
        {"type": "radio", "value": None},
        {"type": "radio", "value": "c"},
    ):
        with warnings.catch_warnings(record=True) as rec:
            warnings.simplefilter("always")
            r.render(create_element("input", props))
        assert not any("changing a controlled input" in str(w.message).lower() for w in rec)
        assert not any("changing an uncontrolled input" in str(w.message).lower() for w in rec)


@pytest.mark.skipif(not is_dev(), reason="radio controlled DEV warnings")
def test_should_not_warn_if_radio_value_changes_but_never_becomes_uncontrolled_0bc1b677() -> None:
    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        r.render(create_element("input", {"type": "radio", "checked": None, "onChange": _noop}))
    node = _host(c)
    assert is_checked_dirty(node)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("input", {"type": "radio", "checked": None, "value": "a", "onChange": _noop}))
    assert not any("uncontrolled" in str(w.message).lower() for w in rec)
    assert_input_tracking_is_current(c)


def _build_hydrate_radio_container(*, controlled: bool) -> tuple[Container, list[ElementNode]]:
    c = Container()
    wrapper = ElementNode(tag="div")
    logs: list[str] = []

    def click_a() -> None:
        logs.append("click a")

    def click_b() -> None:
        logs.append("click b")

    def click_c() -> None:
        logs.append("click c")

    props_a: dict[str, Any] = {"type": "radio", "name": "g", "value": "a", "onClick": click_a}
    props_b: dict[str, Any] = {"type": "radio", "name": "g", "value": "b", "onClick": click_b}
    props_c: dict[str, Any] = {"type": "radio", "name": "g", "value": "c", "onClick": click_c}
    if controlled:
        props_a["checked"] = True
        props_b["checked"] = False
        props_c["checked"] = False
        props_a["onChange"] = _noop
        props_b["onChange"] = _noop
    else:
        props_a["defaultChecked"] = True

    for props in (props_a, props_b, props_c):
        wrapper.append_child(ElementNode(tag="input", props=dict(props)))
    c.root.append_child(wrapper)
    return c, [ch for ch in wrapper.children if isinstance(ch, ElementNode)]


def test_should_hydrate_uncontrolled_radio_buttons_59c43dbe() -> None:
    c, (a, b, _c) = _build_hydrate_radio_container(controlled=False)
    assert a.checked and not b.checked
    b.set_untracked_checked(True)
    assert is_checked_dirty(a) and is_checked_dirty(b)

    def App() -> object:
        return create_element(
            "div",
            None,
            create_element("input", {"type": "radio", "name": "g", "value": "a", "defaultChecked": True}),
            create_element("input", {"type": "radio", "name": "g", "value": "b"}),
            create_element("input", {"type": "radio", "name": "g", "value": "c"}),
        )

    hydrate_root(c, create_element(App, None))
    assert not a.checked and b.checked


def test_should_hydrate_controlled_radio_buttons_fa147524() -> None:
    c, (a, b, _c) = _build_hydrate_radio_container(controlled=True)
    b.set_untracked_checked(True)

    def App() -> object:
        cur, _set = use_state("a")

        def _radio(val: str) -> object:
            return create_element(
                "input",
                {
                    "type": "radio",
                    "name": "g",
                    "value": val,
                    "checked": cur == val,
                    "onChange": _noop,
                },
            )

        return create_element("div", None, _radio("a"), _radio("b"), _radio("c"))

    hydrate_root(c, create_element(App, None))
    assert not a.checked and b.checked


class _LegacyRadioA(Component):
    def render(self) -> object:
        if not self._state:
            self._state["changed"] = False
        return create_element(
            "label",
            None,
            create_element(
                "input",
                {
                    "ref": lambda n: setattr(self, "_a", n),
                    "type": "radio",
                    "name": "fruit",
                    "checked": False,
                    "onChange": self._handle,
                },
            ),
            "A",
        )

    def _handle(self, _: SyntheticEvent) -> None:
        self.set_state({"changed": True})


class _LegacyRadioB(Component):
    def render(self) -> object:
        return create_element(
            "label",
            None,
            create_element("input", {"type": "radio", "name": "fruit", "checked": True, "onChange": _noop}),
            "B",
        )


def test_should_control_radio_buttons_if_tree_updates_during_render_in_legacy_mode_83b85cc4() -> None:
    parent = Container()
    mount = ElementNode(tag="div")
    parent.root.append_child(mount)
    c1 = Container()
    c1_root = create_root(c1)
    c2 = Container()
    mounted = {"done": False}

    def mount_sibling() -> None:
        if mounted["done"]:
            return
        mounted["done"] = True
        c2_root = create_root(c2)
        c2_root.render(create_element(_LegacyRadioB, None))
        for ch in list(c2.root.children):
            mount.append_child(ch)

    class LegacyA(_LegacyRadioA):
        def _handle(self, ev: SyntheticEvent) -> None:
            super()._handle(ev)
            mount_sibling()

    c1_root.render(create_element(LegacyA, None))
    a_inputs = [n for n in c1.query_selector_all("input")]
    assert a_inputs
    a_node = a_inputs[0]
    a_node.dispatch_event("click")
    b_inputs = [n for n in c2.query_selector_all("input")]
    assert b_inputs
    assert b_inputs[0].checked is True
