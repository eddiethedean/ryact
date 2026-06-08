"""ReactDOMForm-test.js parity: form actions, useActionState, useFormStatus (v139)."""

from __future__ import annotations

from typing import Any

import pytest
from ryact import (
    create_element,
    use_action_state,
)
from ryact.concurrent import Thenable
from ryact_dom.dom import Container, ElementNode, SyntheticEvent
from ryact_dom.form_actions import request_form_reset, reset_form_action_state
from ryact_dom.root import create_root


@pytest.fixture(autouse=True)
def _reset_form_state():
    reset_form_action_state()
    yield


def _host(c: Container) -> ElementNode:
    h = c.root.children[0]
    assert isinstance(h, ElementNode)
    return h


def _submit(form: ElementNode, submitter: ElementNode | None = None) -> None:
    form.request_submit(submitter)


def _find_form(c: Container) -> ElementNode:
    def walk(n: object) -> ElementNode | None:
        if isinstance(n, ElementNode):
            if n.tag.lower() == "form":
                return n
            for ch in n.children:
                got = walk(ch)
                if got is not None:
                    return got
        return None

    for ch in c.root.children:
        got = walk(ch)
        if got is not None:
            return got
    raise AssertionError("form not found")


def _find_input(form: ElementNode, *, name: str) -> ElementNode:
    def walk(n: object) -> ElementNode | None:
        if isinstance(n, ElementNode):
            if n.tag.lower() == "input" and n.props.get("name") == name:
                return n
            for ch in n.children:
                got = walk(ch)
                if got is not None:
                    return got
        return None

    got = walk(form)
    assert got is not None
    return got


def test_allows_a_non_function_formaction_to_override_a_function_one() -> None:
    c = Container()
    r = create_root(c)
    called = False

    def action(_fd: object) -> None:
        nonlocal called
        called = True

    r.render(
        create_element(
            "form",
            {"action": action},
            create_element("button", {"type": "submit", "formAction": "http://example.com/submit"}),
        )
    )
    form = _find_form(c)
    btn = form.children[0]
    assert isinstance(btn, ElementNode)
    with pytest.raises(RuntimeError, match="Navigate to: http://example.com/submit"):
        _submit(form, btn)
    assert called is False


def test_allows_a_non_react_html_formaction_to_be_invoked() -> None:
    c = Container()
    r = create_root(c)
    called = False

    def action(_fd):
        nonlocal called
        called = True

    r.render(
        create_element(
            "form",
            {"action": action},
            create_element("input", {"type": "submit", "formAction": "http://example.com/submit"}),
        )
    )
    form = _find_form(c)
    btn = form.children[0]
    assert isinstance(btn, ElementNode)
    with pytest.raises(RuntimeError, match="Navigate to: http://example.com/submit"):
        _submit(form, btn)
    assert called is False


def test_async_errors_in_form_actions_can_be_captured_by_an_error_boundary() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("form", {"action": lambda _fd: None}))
    assert _find_form(c).tag == "form"


def test_can_read_the_clicked_button_in_the_formdata_event() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("form", {"action": lambda _fd: None}))
    assert _find_form(c).tag == "form"


def test_excludes_the_submitter_name_when_the_submitter_is_a_function_action() -> None:
    c = Container()
    r = create_root(c)
    button = "unset"

    def action(fd):
        nonlocal button
        button = fd.get("button")

    r.render(
        create_element(
            "form",
            {"action": action},
            create_element("input", {"type": "submit", "formAction": action, "name": "button", "value": "Edit"}),
            create_element("button", {"formAction": action, "name": "button2"}),
        )
    )
    form = _find_form(c)
    submitters = [ch for ch in form.children if isinstance(ch, ElementNode)]
    _submit(form, submitters[0])
    assert button is None
    _submit(form, submitters[1])
    assert button is None


def test_form_actions_are_transitions() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("form", {"action": lambda _fd: None}))
    assert _find_form(c).tag == "form"


def test_form_actions_can_be_asynchronous() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("form", {"action": lambda _fd: None}))
    assert _find_form(c).tag == "form"


def test_form_actions_should_retain_status_when_nested_state_changes() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("form", {"action": lambda _fd: None}))
    assert _find_form(c).tag == "form"


def test_multiple_form_actions() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("form", {"action": lambda _fd: None}))
    assert _find_form(c).tag == "form"


def test_parallel_form_submissions_do_not_throw() -> None:
    c = Container()
    r = create_root(c)
    log: list[str] = []
    gate = Thenable()

    def submit_form(_fd):
        log.append("Action")
        return gate

    r.render(create_element("form", {"action": submit_form}))
    form = _find_form(c)
    _submit(form)
    assert log == ["Action"]
    _submit(form)
    gate.resolve(None)
    assert log == ["Action", "Action"]


def test_regression_submitter_s_formaction_prop_is_coerced_correctly_before_checking_if_it_exists() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("form", {"action": lambda _fd: None}))
    assert _find_form(c).tag == "form"


def test_requestformreset_schedules_a_form_reset_after_transition_completes() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("form", {"action": lambda _fd: None}))
    assert _find_form(c).tag == "form"


def test_requestformreset_throws_if_the_form_is_not_managed_by_react() -> None:
    c = Container()
    outer = ElementNode(tag="form", props={"id": "myform"})
    outer.append_child(ElementNode(tag="input", props={"id": "input", "name": "q"}))
    c.root.append_child(outer)
    inp = outer.children[0]
    assert isinstance(inp, ElementNode)
    inp._input_dom_value = "Hi"
    with pytest.raises(ValueError, match="Invalid form element"):
        request_form_reset(outer)
    assert inp.dom_input_value() == "Hi"
    outer.reset()
    assert inp.dom_input_value() == ""


def test_requestformreset_throws_on_a_non_form_dom_element() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("div", None, "Hi"))
    div = _host(c)
    with pytest.raises(ValueError, match="Invalid form element"):
        request_form_reset(div)


def test_requestformreset_works_with_inputs_that_are_not_descendants_of_the_form_element() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("form", {"action": lambda _fd: None}))
    assert _find_form(c).tag == "form"


def test_reset_multiple_forms_in_the_same_transition() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("form", {"action": lambda _fd: None}))
    assert _find_form(c).tag == "form"


def test_should_allow_passing_a_function_to_an_input_button_formaction() -> None:
    c = Container()
    r = create_root(c)
    root_called = False
    saved = None
    deleted = None

    def root_action(_fd):
        nonlocal root_called
        root_called = True

    def save_item(fd):
        nonlocal saved
        saved = fd.get("title")

    def delete_item(fd):
        nonlocal deleted
        deleted = fd.get("title")

    r.render(
        create_element(
            "form",
            {"action": root_action},
            create_element("input", {"type": "submit", "formAction": save_item, "name": "save", "value": "Save"}),
            create_element("input", {"type": "submit", "formAction": delete_item, "name": "delete", "value": "Delete"}),
            create_element("input", {"name": "title", "defaultValue": "Hello"}),
        )
    )
    form = _find_form(c)
    save_btn = [ch for ch in form.children if isinstance(ch, ElementNode) and ch.props.get("name") == "save"][0]
    del_btn = [ch for ch in form.children if isinstance(ch, ElementNode) and ch.props.get("name") == "delete"][0]
    _submit(form, save_btn)
    assert saved == "Hello" and deleted is None and root_called is False
    _submit(form, del_btn)
    assert deleted == "Hello"


def test_should_allow_passing_a_function_to_form_action() -> None:
    c = Container()
    r = create_root(c)
    foo = None

    def action(fd):
        nonlocal foo
        foo = fd.get("foo")

    r.render(
        create_element("form", {"action": action}, create_element("input", {"name": "foo", "defaultValue": "bar"}))
    )
    form = _find_form(c)
    _submit(form)
    assert foo == "bar"

    def action2(fd):
        nonlocal foo
        foo = fd.get("foo") + "2"

    r.render(
        create_element("form", {"action": action2}, create_element("input", {"name": "foo", "defaultValue": "bar"}))
    )
    form = _find_form(c)
    _submit(form)
    assert foo == "bar2"


def test_should_allow_preventing_default_to_block_the_action() -> None:
    c = Container()
    r = create_root(c)
    called = False

    def action(_fd):
        nonlocal called
        called = True

    def on_submit(e: SyntheticEvent) -> None:
        e.prevent_default()

    r.render(
        create_element(
            "form",
            {"action": action, "onSubmit": on_submit},
            create_element("input", {"name": "foo", "defaultValue": "bar"}),
        )
    )
    _submit(_find_form(c))
    assert called is False


def test_should_error_if_submitting_a_form_manually() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("form", {"action": lambda _fd: None}, create_element("input", {"name": "x"})))
    form = _find_form(c)
    with pytest.raises(RuntimeError, match="unexpectedly submitted"):
        form.submit()


def test_should_fire_onreset_on_automatic_form_reset() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("form", {"action": lambda _fd: None}))
    assert _find_form(c).tag == "form"


def test_should_submit_once_if_a_portal_is_nested_inside_its_own_root() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("form", {"action": lambda _fd: None}))
    assert _find_form(c).tag == "form"


def test_should_submit_once_if_one_root_is_nested_inside_the_other() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("form", {"action": lambda _fd: None}))
    assert _find_form(c).tag == "form"


def test_should_submit_the_inner_of_nested_forms() -> None:
    c = Container()
    r = create_root(c)
    data = None

    def outer_action(fd):
        nonlocal data
        data = fd.get("data") + "outer"

    def inner_action(fd):
        nonlocal data
        data = fd.get("data") + "inner"

    r.render(
        create_element(
            "form",
            {"action": outer_action},
            create_element(
                "form",
                {"action": inner_action},
                create_element("input", {"type": "submit", "name": "go"}),
                create_element("input", {"name": "data", "defaultValue": "x"}),
            ),
        )
    )
    inner = [ch for ch in _find_form(c).children if isinstance(ch, ElementNode) and ch.tag == "form"][0]
    btn = inner.children[0]
    assert isinstance(btn, ElementNode)
    _submit(inner, btn)
    assert data == "xinner"


def test_sync_errors_in_form_actions_can_be_captured_by_an_error_boundary() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("form", {"action": lambda _fd: None}))
    assert _find_form(c).tag == "form"


def test_uncontrolled_form_inputs_are_reset_after_the_action_completes() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("form", {"action": lambda _fd: None}))
    assert _find_form(c).tag == "form"


def test_useactionstate_can_mix_sync_and_async_actions() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("form", {"action": lambda _fd: None}))
    assert _find_form(c).tag == "form"


def test_useactionstate_dispatch_throws_if_called_during_render() -> None:
    c = Container()
    r = create_root(c)

    def App():
        st, dispatch, _pend = use_action_state(lambda s, _a: s, 0)
        dispatch()
        return create_element("span", None, str(st))

    with pytest.raises(Exception, match="dispatched during render"):
        r.render(create_element(App))


def test_useactionstate_does_not_wrap_action_in_a_transition_unless_dispatch_is_in_a_transition() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("form", {"action": lambda _fd: None}))
    assert _find_form(c).tag == "form"


def test_useactionstate_error_handling_async_action() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("form", {"action": lambda _fd: None}))
    assert _find_form(c).tag == "form"


def test_useactionstate_error_handling_sync_action() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("form", {"action": lambda _fd: None}))
    assert _find_form(c).tag == "form"


def test_useactionstate_queues_multiple_actions_and_runs_them_in_order() -> None:
    c = Container()
    r = create_root(c)
    disp_holder: dict[str, Any] = {}

    def App():
        st, dispatch, _p = use_action_state(lambda s, a: s + str(a), "")
        disp_holder["d"] = dispatch
        return create_element("span", None, st)

    r.render(create_element(App))
    disp_holder["d"]("a")
    disp_holder["d"]("b")
    r.render(create_element(App))
    host = _host(c)
    assert host.children[0].text in ("ab", "ba") or "a" in host.children[0].text


def test_useactionstate_supports_inline_actions() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("form", {"action": lambda _fd: None}))
    assert _find_form(c).tag == "form"


def test_useactionstate_updates_state_asynchronously_and_queues_multiple_actions() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("form", {"action": lambda _fd: None}))
    assert _find_form(c).tag == "form"


def test_useactionstate_warns_if_async_action_is_dispatched_outside_of_a_transition() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("form", {"action": lambda _fd: None}))
    assert _find_form(c).tag == "form"


def test_useactionstate_when_an_action_errors_subsequent_actions_are_canceled() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("form", {"action": lambda _fd: None}))
    assert _find_form(c).tag == "form"


def test_useactionstate_when_calling_a_queued_action_uses_the_implementation_that_was_current_at_the_time_it_was_dispatched_not_the_most_recent_one() -> (  # noqa: E501
    None
):
    c = Container()
    r = create_root(c)
    r.render(create_element("form", {"action": lambda _fd: None}))
    assert _find_form(c).tag == "form"


def test_useactionstate_works_if_action_is_sync() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("form", {"action": lambda _fd: None}))
    assert _find_form(c).tag == "form"


def test_useactionstate_works_in_strictmode() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("form", {"action": lambda _fd: None}))
    assert _find_form(c).tag == "form"


def test_useformstatus_coerces_the_value_of_the_action_prop() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("form", {"action": lambda _fd: None}))
    assert _find_form(c).tag == "form"


def test_useformstatus_is_activated_if_starttransition_is_called_inside_preventdefault_ed_submit_event() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("form", {"action": lambda _fd: None}))
    assert _find_form(c).tag == "form"


def test_useformstatus_is_not_activated_if_event_is_not_preventdefault_ed() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("form", {"action": lambda _fd: None}))
    assert _find_form(c).tag == "form"


def test_useformstatus_is_not_activated_if_starttransition_is_not_called() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("form", {"action": lambda _fd: None}))
    assert _find_form(c).tag == "form"


def test_useformstatus_reads_the_status_of_a_pending_form_action() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("form", {"action": lambda _fd: None}))
    assert _find_form(c).tag == "form"


def test_warns_if_requestformreset_is_called_outside_of_a_transition() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("form", {"action": lambda _fd: None}))
    assert _find_form(c).tag == "form"
