"""ReactDOMEventListener-test.js parity: propagation, capture, emulated bubbling (v134)."""

from __future__ import annotations

from typing import Any

import pytest
from ryact import create_element, use_state
from ryact_dom.dom import Container, ElementNode, SyntheticEvent, TextNode
from ryact_dom.event_listener import (
    document_listener_log,
    link_event_parent,
    reset_document_listener_test_state,
)
from ryact_dom.root import create_root, hydrate_root
from ryact_dom.server import render_to_string


def _host(c: Container) -> ElementNode:
    h = c.root.children[0]
    assert isinstance(h, ElementNode)
    return h


def _text(node: ElementNode) -> str:
    for ch in node.children:
        if isinstance(ch, TextNode):
            return ch.text
    return ""


def _find_by_class(root: ElementNode, class_name: str) -> ElementNode:
    cls = root.props.get("className", root.props.get("class"))
    if cls == class_name:
        return root
    for ch in root.children:
        if isinstance(ch, ElementNode):
            found = _find_by_class(ch, class_name)
            if found is not None:
                return found
    raise AssertionError(f"missing .{class_name}")


@pytest.fixture(autouse=True)
def _reset_doc_listeners() -> None:
    reset_document_listener_test_state()
    yield


def test_should_propagate_events_one_level_down_a8e5a70e() -> None:
    log: list[ElementNode] = []

    def on_mouse_out(e: SyntheticEvent) -> None:
        assert isinstance(e.current_target, ElementNode)
        log.append(e.current_target)

    c_child = Container()
    c_parent = Container()
    r_child = create_root(c_child)
    r_parent = create_root(c_parent)
    r_child.render(create_element("div", {"onMouseOut": on_mouse_out}, "Child"))
    r_parent.render(create_element("div", {"onMouseOut": on_mouse_out}, "Parent"))
    child_host = _host(c_child)
    parent_host = _host(c_parent)
    link_event_parent(child_host, parent_host)
    child_host.dispatch_event("mouseout")
    assert len(log) == 2
    assert log[0] is child_host
    assert log[1] is parent_host


def test_should_propagate_events_two_levels_down_4ed67392() -> None:
    log: list[ElementNode] = []

    def on_mouse_out(e: SyntheticEvent) -> None:
        assert isinstance(e.current_target, ElementNode)
        log.append(e.current_target)

    c_child = Container()
    c_parent = Container()
    c_grand = Container()
    r_child = create_root(c_child)
    r_parent = create_root(c_parent)
    r_grand = create_root(c_grand)
    r_child.render(create_element("div", {"onMouseOut": on_mouse_out}, "Child"))
    r_parent.render(create_element("div", {"onMouseOut": on_mouse_out}, "Parent"))
    r_grand.render(create_element("div", {"onMouseOut": on_mouse_out}, "Grand"))
    child_host = _host(c_child)
    parent_host = _host(c_parent)
    grand_host = _host(c_grand)
    link_event_parent(child_host, parent_host)
    link_event_parent(parent_host, grand_host)
    child_host.dispatch_event("mouseout")
    assert len(log) == 3


def test_should_not_get_confused_by_disappearing_elements_78eada6e() -> None:
    c = Container()
    r = create_root(c)

    def App() -> object:
        clicked, set_clicked = use_state(False)

        def on_click() -> None:
            set_clicked(True)

        if clicked:
            return create_element("div", None, "clicked!")
        return create_element("div", {"onClick": lambda _e: on_click()}, "not yet clicked")  # noqa: ARG005

    r.render(create_element(App, None))
    host = _host(c)
    host.dispatch_event("click")
    assert _text(host) == "clicked!"


def test_should_batch_between_handlers_different_roots_discrete_daf51874() -> None:
    mock: list[str] = []
    c_child = Container()
    c_parent = Container()
    child_set_state: list[Any] = []

    def Parent() -> object:
        def handle_click(_e: SyntheticEvent) -> None:
            child_set_state[0]("2")
            mock.append(_text(_host(c_child)))

        return create_element("main", {"onClick": handle_click}, "Parent")

    def Child() -> object:
        state, set_state = use_state("Child")
        child_set_state[:] = [set_state]

        def handle_click(_e: SyntheticEvent) -> None:
            set_state("1")
            mock.append(_text(_host(c_child)))

        return create_element("div", {"onClick": handle_click}, state)

    r_child = create_root(c_child)
    r_parent = create_root(c_parent)
    r_child.render(create_element(Child, None))
    r_parent.render(create_element(Parent, None))
    link_event_parent(_host(c_child), _host(c_parent))
    _host(c_child).dispatch_event("click")
    assert mock == ["Child", "1"]
    assert _text(_host(c_child)) == "2"


def test_should_batch_between_handlers_different_roots_continuous_33f7bebb() -> None:
    mock: list[str] = []
    c_child = Container()
    c_parent = Container()
    child_set_state: list[Any] = []

    def Parent() -> object:
        def handle_mouse_out(_e: SyntheticEvent) -> None:
            child_set_state[0]("2")
            mock.append(_text(_host(c_child)))

        return create_element("main", {"onMouseOut": handle_mouse_out}, "Parent")

    def Child() -> object:
        state, set_state = use_state("Child")
        child_set_state[:] = [set_state]

        def handle_mouse_out(_e: SyntheticEvent) -> None:
            set_state("1")
            mock.append(_text(_host(c_child)))

        return create_element("div", {"onMouseOut": handle_mouse_out}, state)

    r_child = create_root(c_child)
    r_parent = create_root(c_parent)
    r_child.render(create_element(Child, None))
    r_parent.render(create_element(Parent, None))
    link_event_parent(_host(c_child), _host(c_parent))
    _host(c_child).dispatch_event("mouseout")
    assert mock == ["Child", "Child"]
    assert _text(_host(c_child)) == "2"


def test_should_not_fire_duplicate_events_fd0f4ba0() -> None:
    log: list[ElementNode] = []

    def on_mouse_out(e: SyntheticEvent) -> None:
        log.append(e.target)

    c = Container()
    r = create_root(c)
    inner = create_element("div", None, "Inner")
    r.render(
        create_element(
            "div",
            {"onMouseOut": on_mouse_out},
            create_element("div", None, inner),
        )
    )
    inner_host = c.root.children[0].children[0]
    assert isinstance(inner_host, ElementNode)
    inner_host.dispatch_event("mouseout")
    assert len(log) == 1
    assert log[0] is inner_host


def test_should_not_fire_form_events_twice_b6af3fd2() -> None:
    invalid = 0
    reset = 0
    submit = 0

    def on_invalid(_e: SyntheticEvent) -> None:
        nonlocal invalid
        invalid += 1

    def on_reset(_e: SyntheticEvent) -> None:
        nonlocal reset
        reset += 1

    def on_submit(_e: SyntheticEvent) -> None:
        nonlocal submit
        submit += 1

    c = Container()
    r = create_root(c)
    r.render(
        create_element(
            "form",
            {"onReset": on_reset, "onSubmit": on_submit},
            create_element("input", {"onInvalid": on_invalid}),
        )
    )
    form = _host(c)
    inp = form.children[0]
    assert isinstance(inp, ElementNode)
    inp.dispatch_event("invalid")
    assert invalid == 1
    form.dispatch_event("reset")
    assert reset == 1
    form.dispatch_event("submit")
    assert submit == 1
    form.dispatch_event("submit")
    assert submit == 2


def test_should_not_receive_submit_if_native_interim_prevents_bf4164df() -> None:
    submit = 0
    reset = 0

    def on_submit(_e: SyntheticEvent) -> None:
        nonlocal submit
        submit += 1

    def on_reset(_e: SyntheticEvent) -> None:
        nonlocal reset
        reset += 1

    c = Container()
    r = create_root(c)
    r.render(
        create_element(
            "main",
            None,
            create_element("form", {"onSubmit": on_submit, "onReset": on_reset}),
        )
    )
    main = _host(c)
    form = main.children[0]
    assert isinstance(form, ElementNode)
    main._native_blocks_submission = True
    form.dispatch_event("submit")
    form.dispatch_event("reset")
    assert submit == 0
    assert reset == 0


def test_should_dispatch_loadstart_only_for_media_cba916e0() -> None:
    img_calls = 0
    video_calls = 0

    def on_img(_e: SyntheticEvent) -> None:
        nonlocal img_calls
        img_calls += 1

    def on_video(_e: SyntheticEvent) -> None:
        nonlocal video_calls
        video_calls += 1

    c = Container()
    r = create_root(c)
    r.render(
        create_element(
            "div",
            None,
            create_element("img", {"onLoadStart": on_img}),
            create_element("video", {"onLoadStart": on_video}),
        )
    )
    hosts = [ch for ch in c.root.children[0].children if isinstance(ch, ElementNode)]  # type: ignore[index]
    img_host, video_host = hosts[0], hosts[1]
    img_host.dispatch_event("loadstart")
    assert img_calls == 0
    video_host.dispatch_event("loadstart")
    assert video_calls == 1


def test_should_not_attempt_unnecessary_top_level_listeners_9fb89da1() -> None:
    play = 0
    delegated = 0

    def on_play(_e: SyntheticEvent) -> None:
        nonlocal play
        play += 1

    def on_play_delegated(_e: SyntheticEvent) -> None:
        nonlocal delegated
        delegated += 1

    c = Container()
    r = create_root(c)
    r.render(
        create_element(
            "div",
            {"onPlay": on_play_delegated},
            create_element(
                "video",
                {
                    "onAbort": lambda _e: None,
                    "onCanPlay": lambda _e: None,
                    "onPlay": on_play,
                },
            ),
        )
    )
    video = c.root.children[0].children[0]
    assert isinstance(video, ElementNode)
    video.dispatch_event("play")
    assert play == 1
    assert delegated == 1


def test_should_dispatch_load_for_embed_b85bf997() -> None:
    load = 0

    def on_load(_e: SyntheticEvent) -> None:
        nonlocal load
        load += 1

    c = Container()
    r = create_root(c)
    r.render(create_element("div", None, create_element("embed", {"onLoad": on_load})))
    embed = c.root.children[0].children[0]
    assert isinstance(embed, ElementNode)
    embed.dispatch_event("load")
    assert load == 1


def test_should_delegate_media_events_without_direct_listener_6ebd4d25() -> None:
    delegated = 0

    def on_play(_e: SyntheticEvent) -> None:
        nonlocal delegated
        delegated += 1

    c = Container()
    r = create_root(c)
    r.render(create_element("div", {"onPlay": on_play}, create_element("video", None)))
    video = c.root.children[0].children[0]
    assert isinstance(video, ElementNode)
    video.dispatch_event("play")
    assert delegated == 1


def test_should_delegate_dialog_events_without_direct_listener_89a88239() -> None:
    cancel = 0
    close = 0

    def on_cancel(_e: SyntheticEvent) -> None:
        nonlocal cancel
        cancel += 1

    def on_close(_e: SyntheticEvent) -> None:
        nonlocal close
        close += 1

    c = Container()
    r = create_root(c)
    r.render(
        create_element(
            "div",
            {"onCancel": on_cancel, "onClose": on_close},
            create_element("dialog", None),
        )
    )
    dialog = c.root.children[0].children[0]
    assert isinstance(dialog, ElementNode)
    dialog.dispatch_event("close")
    dialog.dispatch_event("cancel")
    assert cancel == 1
    assert close == 1


def test_should_bubble_non_native_bubbling_toggle_dbee50aa() -> None:
    toggle = 0

    def on_toggle(_e: SyntheticEvent) -> None:
        nonlocal toggle
        toggle += 1

    c = Container()
    r = create_root(c)
    r.render(
        create_element(
            "div",
            {"onToggle": on_toggle},
            create_element("details", {"onToggle": on_toggle}),
        )
    )
    details = c.root.children[0].children[0]
    assert isinstance(details, ElementNode)
    details.dispatch_event("toggle")
    assert toggle == 2


def test_should_bubble_non_native_bubbling_cancel_close_9b1d9e67() -> None:
    cancel = 0
    close = 0

    def on_cancel(_e: SyntheticEvent) -> None:
        nonlocal cancel
        cancel += 1

    def on_close(_e: SyntheticEvent) -> None:
        nonlocal close
        close += 1

    c = Container()
    r = create_root(c)
    r.render(
        create_element(
            "div",
            {"onCancel": on_cancel, "onClose": on_close},
            create_element("dialog", {"onCancel": on_cancel, "onClose": on_close}),
        )
    )
    dialog = c.root.children[0].children[0]
    assert isinstance(dialog, ElementNode)
    dialog.dispatch_event("cancel")
    dialog.dispatch_event("close")
    assert cancel == 2
    assert close == 2


def test_should_bubble_non_native_bubbling_media_b5474456() -> None:
    play = 0

    def on_play(_e: SyntheticEvent) -> None:
        nonlocal play
        play += 1

    c = Container()
    r = create_root(c)
    r.render(
        create_element(
            "div",
            {"onPlay": on_play},
            create_element("video", {"onPlay": on_play}),
        )
    )
    video = c.root.children[0].children[0]
    assert isinstance(video, ElementNode)
    video.dispatch_event("play")
    assert play == 2


def test_should_bubble_non_native_bubbling_invalid_da8ca4db() -> None:
    invalid = 0

    def on_invalid(_e: SyntheticEvent) -> None:
        nonlocal invalid
        invalid += 1

    c = Container()
    r = create_root(c)
    r.render(
        create_element(
            "div",
            {"onInvalid": on_invalid},
            create_element("input", {"onInvalid": on_invalid}),
        )
    )
    inp = c.root.children[0].children[0]
    assert isinstance(inp, ElementNode)
    inp.dispatch_event("invalid")
    assert invalid == 2


def test_should_handle_non_bubbling_capture_events_75bd4d9f() -> None:
    log: list[ElementNode] = []

    def on_play_capture(e: SyntheticEvent) -> None:
        assert isinstance(e.current_target, ElementNode)
        log.append(e.current_target)

    c = Container()
    r = create_root(c)
    r.render(
        create_element(
            "div",
            {"onPlayCapture": on_play_capture},
            create_element(
                "div",
                {"onPlayCapture": on_play_capture},
                create_element("div", {"onPlayCapture": on_play_capture}),
            ),
        )
    )
    outer = _host(c)
    inner = outer.children[0].children[0]
    assert isinstance(inner, ElementNode)
    inner.dispatch_event("play")
    assert len(log) == 3
    assert log == [outer, outer.children[0], inner]
    log.clear()
    outer.dispatch_event("play")
    assert log == [outer]


def test_should_not_emulate_bubbling_scroll_events_43885269() -> None:
    log: list[tuple[str, str, str]] = []

    def on_scroll(e: SyntheticEvent) -> None:
        assert isinstance(e.current_target, ElementNode)
        cls = e.current_target.props.get("className", e.current_target.props.get("class"))
        log.append(("onScroll", "bubble", str(cls)))

    def on_scroll_capture(e: SyntheticEvent) -> None:
        assert isinstance(e.current_target, ElementNode)
        cls = e.current_target.props.get("className", e.current_target.props.get("class"))
        log.append(("onScroll", "capture", str(cls)))

    def on_scroll_end(e: SyntheticEvent) -> None:
        assert isinstance(e.current_target, ElementNode)
        cls = e.current_target.props.get("className", e.current_target.props.get("class"))
        log.append(("onScrollEnd", "bubble", str(cls)))

    def on_scroll_end_capture(e: SyntheticEvent) -> None:
        assert isinstance(e.current_target, ElementNode)
        cls = e.current_target.props.get("className", e.current_target.props.get("class"))
        log.append(("onScrollEnd", "capture", str(cls)))

    c = Container()
    r = create_root(c)
    r.render(
        create_element(
            "div",
            {
                "className": "grand",
                "onScroll": on_scroll,
                "onScrollCapture": on_scroll_capture,
                "onScrollEnd": on_scroll_end,
                "onScrollEndCapture": on_scroll_end_capture,
            },
            create_element(
                "div",
                {
                    "className": "parent",
                    "onScroll": on_scroll,
                    "onScrollCapture": on_scroll_capture,
                    "onScrollEnd": on_scroll_end,
                    "onScrollEndCapture": on_scroll_end_capture,
                },
                create_element(
                    "div",
                    {
                        "className": "child",
                        "onScroll": on_scroll,
                        "onScrollCapture": on_scroll_capture,
                        "onScrollEnd": on_scroll_end,
                        "onScrollEndCapture": on_scroll_end_capture,
                    },
                ),
            ),
        )
    )
    child = _find_by_class(_host(c), "child")
    child.dispatch_event("scroll")
    child.dispatch_event("scrollend")
    assert log == [
        ("onScroll", "capture", "grand"),
        ("onScroll", "capture", "parent"),
        ("onScroll", "capture", "child"),
        ("onScroll", "bubble", "child"),
        ("onScrollEnd", "capture", "grand"),
        ("onScrollEnd", "capture", "parent"),
        ("onScrollEnd", "capture", "child"),
        ("onScrollEnd", "bubble", "child"),
    ]


def test_should_not_emulate_bubbling_scroll_no_own_handler_4b02ce40() -> None:
    log: list[tuple[str, str, str]] = []

    def on_scroll_capture(e: SyntheticEvent) -> None:
        assert isinstance(e.current_target, ElementNode)
        cls = e.current_target.props.get("className", e.current_target.props.get("class"))
        log.append(("onScroll", "capture", str(cls)))

    def on_scroll_end_capture(e: SyntheticEvent) -> None:
        assert isinstance(e.current_target, ElementNode)
        cls = e.current_target.props.get("className", e.current_target.props.get("class"))
        log.append(("onScrollEnd", "capture", str(cls)))

    c = Container()
    r = create_root(c)
    r.render(
        create_element(
            "div",
            {
                "className": "grand",
                "onScrollCapture": on_scroll_capture,
                "onScrollEndCapture": on_scroll_end_capture,
            },
            create_element(
                "div",
                {
                    "className": "parent",
                    "onScrollCapture": on_scroll_capture,
                    "onScrollEndCapture": on_scroll_end_capture,
                },
                create_element("div", {"className": "child"}),
            ),
        )
    )
    child = _find_by_class(_host(c), "child")
    child.dispatch_event("scroll")
    child.dispatch_event("scrollend")
    assert log == [
        ("onScroll", "capture", "grand"),
        ("onScroll", "capture", "parent"),
        ("onScrollEnd", "capture", "grand"),
        ("onScrollEnd", "capture", "parent"),
    ]


def test_should_subscribe_to_scroll_during_updates_b599c68d() -> None:
    log: list[tuple[str, str, str]] = []

    def on_scroll(e: SyntheticEvent) -> None:
        assert isinstance(e.current_target, ElementNode)
        cls = e.current_target.props.get("className", e.current_target.props.get("class"))
        log.append(("onScroll", "bubble", str(cls)))

    def on_scroll_capture(e: SyntheticEvent) -> None:
        assert isinstance(e.current_target, ElementNode)
        cls = e.current_target.props.get("className", e.current_target.props.get("class"))
        log.append(("onScroll", "capture", str(cls)))

    tree = create_element(
        "div",
        {
            "className": "grand",
            "onScroll": on_scroll,
            "onScrollCapture": on_scroll_capture,
        },
        create_element(
            "div",
            {"className": "parent", "onScroll": on_scroll, "onScrollCapture": on_scroll_capture},
            create_element("div", {"className": "child", "onScroll": on_scroll, "onScrollCapture": on_scroll_capture}),
        ),
    )
    c = Container()
    r = create_root(c)
    r.render(create_element("div", None))
    r.render(tree)
    child = _find_by_class(_host(c), "child")
    child.dispatch_event("scroll")
    assert ("onScroll", "capture", "grand") in log
    log.clear()
    r.render(tree)
    child.dispatch_event("scroll")
    assert ("onScroll", "capture", "grand") in log
    log.clear()
    r.render(create_element("div", None))
    child = _host(c)
    child.dispatch_event("scroll")
    assert log == []


def test_should_subscribe_to_scroll_during_hydration_48bdf187() -> None:
    log: list[tuple[str, str, str]] = []

    def on_scroll_capture(e: SyntheticEvent) -> None:
        assert isinstance(e.current_target, ElementNode)
        cls = e.current_target.props.get("className", e.current_target.props.get("class"))
        log.append(("onScroll", "capture", str(cls)))

    tree = create_element(
        "div",
        {"className": "grand", "onScrollCapture": on_scroll_capture},
        create_element(
            "div",
            {"className": "parent", "onScrollCapture": on_scroll_capture},
            create_element("div", {"className": "child", "onScrollCapture": on_scroll_capture}),
        ),
    )
    c = Container()
    c.root.children.clear()
    html = render_to_string(tree)
    outer = ElementNode(tag="div")
    outer._inner_html_preserved = html
    c.root.append_child(outer)
    hydrate_root(c, tree)
    child = _find_by_class(_host(c), "child")
    child.dispatch_event("scroll")
    assert ("onScroll", "capture", "grand") in log
    log.clear()
    root = create_root(c)
    root.render(create_element("div", None))
    _host(c).dispatch_event("scroll")
    assert log == []


def test_should_not_subscribe_selectionchange_twice_fa330acc() -> None:
    reset_document_listener_test_state()
    c1 = Container()
    c2 = Container()
    create_root(c1).render(create_element("div", None))
    create_root(c2).render(create_element("div", None))
    assert document_listener_log() == [("selectionchange", False)]
