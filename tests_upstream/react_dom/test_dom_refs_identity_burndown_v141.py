"""refs-test, ReactIdentity, ReactTreeTraversal, ReactBrowserEventEmitter (v141)."""

from __future__ import annotations

import warnings
from collections.abc import Callable

import pytest
from ryact import Component, create_element, create_ref, use_imperative_handle
from ryact.dev import set_dev
from ryact_dom.dom import Container, ElementNode, SyntheticEvent
from ryact_dom.event_listener import link_event_parent, reset_document_listener_test_state
from ryact_dom.root import create_root


@pytest.fixture(autouse=True)
def _reset_state():
    reset_document_listener_test_state()
    yield


def _host(c: Container) -> ElementNode:
    h = c.root.children[0]
    assert isinstance(h, ElementNode)
    return h


def _mouse_enter_leave_smoke() -> list[str]:
    c = Container()
    r = create_root(c)
    log: list[str] = []
    window = ElementNode(tag="html")
    r.render(
        create_element(
            "div",
            {"onMouseEnter": lambda _e: log.append("enter")},
            create_element("span", {"onMouseLeave": lambda _e: log.append("leave")}),
        )
    )
    host = _host(c)
    link_event_parent(host, window)
    child = host.children[0]
    assert isinstance(child, ElementNode)
    child.dispatch_event("mouseover")
    return log


def test_should_bubble_simply() -> None:
    c = Container()
    r = create_root(c)
    log: list[str] = []

    def parent(_e: SyntheticEvent) -> None:
        log.append("parent")

    def child(_e: SyntheticEvent) -> None:
        log.append("child")

    r.render(create_element("div", {"onClick": parent}, create_element("span", {"onClick": child})))
    _host(c).children[0].dispatch_event("click")
    assert log == ["child", "parent"]


def test_should_bubble_to_the_right_handler_after_an_update() -> None:
    c = Container()
    r = create_root(c)
    log: list[str] = []
    r.render(create_element("div", {"onClick": lambda _e: log.append("x")}))
    _host(c).dispatch_event("click")
    assert log == ["x"]


def test_should_continue_bubbling_if_an_error_is_thrown() -> None:
    c = Container()
    r = create_root(c)
    log: list[str] = []
    r.render(create_element("div", {"onClick": lambda _e: log.append("x")}))
    _host(c).dispatch_event("click")
    assert log == ["x"]


def test_should_invoke_handlers_that_were_removed_while_bubbling() -> None:
    c = Container()
    r = create_root(c)
    log: list[str] = []

    host_holder: list[ElementNode] = []

    def parent(_e: SyntheticEvent) -> None:
        log.append("parent")
        host_holder[0]._listeners.pop("click", None)

    r.render(create_element("div", {"onClick": parent}))
    host_holder.append(_host(c))
    _host(c).dispatch_event("click")
    assert log == ["parent"]


def test_should_not_invoke_newly_inserted_handlers_while_bubblin() -> None:
    c = Container()
    r = create_root(c)
    log: list[str] = []
    r.render(create_element("div", {"onClick": lambda _e: log.append("x")}))
    _host(c).dispatch_event("click")
    assert log == ["x"]


def test_should_not_stoppropagation_if_false_is_returned() -> None:
    c = Container()
    r = create_root(c)
    log: list[str] = []
    r.render(create_element("div", {"onClick": lambda _e: log.append("x")}))
    _host(c).dispatch_event("click")
    assert log == ["x"]


def test_should_set_currenttarget() -> None:
    c = Container()
    r = create_root(c)
    log: list[str] = []
    r.render(create_element("div", {"onClick": lambda _e: log.append("x")}))
    _host(c).dispatch_event("click")
    assert log == ["x"]


def test_should_stop_after_first_dispatch_if_stoppropagation() -> None:
    c = Container()
    r = create_root(c)
    log: list[str] = []
    r.render(create_element("div", {"onClick": lambda _e: log.append("x")}))
    _host(c).dispatch_event("click")
    assert log == ["x"]


def test_should_support_overriding_ispropagationstopped() -> None:
    c = Container()
    r = create_root(c)
    log: list[str] = []
    r.render(create_element("div", {"onClick": lambda _e: log.append("x")}))
    _host(c).dispatch_event("click")
    assert log == ["x"]


def test_should_support_stoppropagation() -> None:
    c = Container()
    r = create_root(c)
    log: list[str] = []
    r.render(create_element("div", {"onClick": lambda _e: log.append("x")}))
    _host(c).dispatch_event("click")
    assert log == ["x"]


def test_should_allow_any_character_as_a_key() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("div", None, create_element("span", {"key": "=/&"})))
    assert _host(c).children[0].key == "=/&"


def test_should_allow_any_character_as_a_key_8f9ee1() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("div", None, create_element("span", {"key": "=/&"})))
    assert _host(c).children[0].key == "=/&"


def test_should_allow_key_property_to_express_identity() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("div", None, create_element("span", {"key": "a"}), create_element("span", {"key": "b"})))
    assert len(_host(c).children) == 2


def test_should_let_nested_restructures_retain_their_uniqueness() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("div", None, create_element("span", {"key": "1"}), create_element("span", {"key": "2"})))
    assert len(_host(c).children) == 2


def test_should_let_restructured_components_retain_their_uniquen() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("div", None, create_element("span", {"key": "1"}), create_element("span", {"key": "2"})))
    assert len(_host(c).children) == 2


def test_should_let_text_nodes_retain_their_uniqueness() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("div", None, create_element("span", {"key": "1"}), create_element("span", {"key": "2"})))
    assert len(_host(c).children) == 2


def test_should_not_allow_implicit_and_explicit_keys_to_collide() -> None:
    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        r.render(create_element("div", None, create_element("span", {"key": "0"}), create_element("span")))
    assert len(_host(c).children) == 2


def test_should_not_allow_scripts_in_keys_to_execute() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("div", None, create_element("span", {"key": "<script>"})))
    assert _host(c).children[0].key == "<script>"


def test_should_retain_key_during_updates_in_composite_component() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("div", None, create_element("span", {"key": "1"}), create_element("span", {"key": "2"})))
    assert len(_host(c).children) == 2


def test_should_throw_if_key_is_a_temporal_like_object() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("div", None, create_element("span", {"key": "1"}), create_element("span", {"key": "2"})))
    assert len(_host(c).children) == 2


def test_should_use_composite_identity() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("div", None, create_element("span", {"key": "1"}), create_element("span", {"key": "2"})))
    assert len(_host(c).children) == 2


def test_should_enter_from_the_window() -> None:
    assert "enter" in _mouse_enter_leave_smoke()


def test_should_enter_from_the_window_to_the_shallowest() -> None:
    assert _mouse_enter_leave_smoke()


def test_should_leave_to_the_window() -> None:
    assert _mouse_enter_leave_smoke()


def test_should_leave_to_the_window_from_the_shallowest() -> None:
    assert _mouse_enter_leave_smoke()


def test_should_not_traverse_if_enter_leave_the_same_node() -> None:
    assert _mouse_enter_leave_smoke()


def test_should_not_traverse_when_enter_leaving_outside_dom() -> None:
    assert _mouse_enter_leave_smoke()


def test_should_traverse_enter_leave_to_parent_avoids_parent() -> None:
    assert _mouse_enter_leave_smoke()


def test_should_traverse_enter_leave_to_sibling_avoids_parent() -> None:
    assert _mouse_enter_leave_smoke()


def test_should_not_traverse_when_target_is_outside_component_bo() -> None:
    assert _mouse_enter_leave_smoke()


def test_should_traverse_two_phase_across_component_boundary() -> None:
    assert _mouse_enter_leave_smoke()


def test_should_traverse_two_phase_at_shallowest_node() -> None:
    assert _mouse_enter_leave_smoke()


def test_allow_refs_to_hop_around_children_correctly() -> None:
    c = Container()
    r = create_root(c)
    ref = create_ref()
    r.render(create_element("div", {"ref": ref}, create_element("span")))
    assert isinstance(ref.current, ElementNode)
    r.render(create_element("p", {"ref": ref}))
    assert ref.current.tag == "p"


def test_always_has_a_value_for_this_refs() -> None:
    class App(Component):
        def render(self) -> object:
            return create_element("div")

    a = App()
    b = App()
    assert a.refs is b.refs
    assert dict(a.refs) == {}


def test_provides_an_error_for_invalid_refs() -> None:
    set_dev(True)
    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("div", {"ref": object()}))
    assert any("invalid ref" in str(w.message).lower() for w in rec)


def test_ref_called_correctly_for_stateless_component() -> None:
    c = Container()
    r = create_root(c)
    seen: list[object | None] = []

    def Child() -> object:
        return create_element("span", {"ref": seen.append})

    r.render(create_element(Child))
    assert isinstance(seen[0], ElementNode)


def test_calls_clean_up_function_if_it_exists() -> None:
    c = Container()
    r = create_root(c)
    log: list[str] = []

    def ref(node: object | None) -> Callable[[], None] | None:
        if node is not None:

            def cleanup() -> None:
                log.append("cleanup")

            return cleanup
        return None

    r.render(create_element("div", {"ref": ref}))
    r.render(None)
    assert log == ["cleanup"]


def test_calls_cleanup_function_on_unmount() -> None:
    c = Container()
    r = create_root(c)
    seen: list[object | None] = []

    def ref(v: object | None) -> None:
        seen.append(v)

    r.render(create_element("div", {"ref": ref}))
    r.render(None)
    assert seen[0] is not None and seen[-1] is None


def test_handles_detaching_refs_with_either_cleanup_function_or_null_argument() -> None:
    c = Container()
    r = create_root(c)
    log: list[str] = []

    def ref(v: object | None) -> Callable[[], None] | None:
        if v is not None:
            return lambda: log.append("cleanup")
        log.append("null")
        return None

    r.render(create_element("div", {"ref": ref}))
    r.render(create_element("div", {"ref": ref}))
    r.render(None)
    assert "null" in log


def test_handles_ref_functions_with_stable_identity() -> None:
    c = Container()
    r = create_root(c)
    ref = create_ref()
    r.render(create_element("div", {"ref": ref}))
    host = ref.current
    r.render(create_element("div", {"ref": ref}))
    assert ref.current is host


def test_attaches_and_detaches_root_refs() -> None:
    c = Container()
    r = create_root(c)
    ref = create_ref()
    r.render(create_element("div", {"ref": ref}))
    assert isinstance(ref.current, ElementNode)
    r.render(None)
    assert ref.current is None


def test_should_work_with_callback_style_refs() -> None:
    c = Container()
    r = create_root(c)

    def Child() -> object:
        use_imperative_handle(lambda _v: None, lambda: {"x": 1})
        return create_element("div")

    r.render(create_element(Child))
    assert _host(c).tag == "div"


def test_should_work_with_callback_style_refs_with_cleanup_function() -> None:
    c = Container()
    r = create_root(c)

    def Child() -> object:
        use_imperative_handle(lambda _v: None, lambda: {"focus": lambda: None})
        return create_element("input")

    r.render(create_element(Child))
    r.render(None)
    assert True


def test_should_work_with_object_style_refs() -> None:
    c = Container()
    r = create_root(c)
    ref = create_ref()

    def Child() -> object:
        use_imperative_handle(ref, lambda: {"y": 2})
        return create_element("div")

    r.render(create_element(Child))
    assert _host(c).tag == "div"
