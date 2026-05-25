"""ReactDOMEventPropagation-test.js parity: event bubbling (v136)."""

# ruff: noqa: E501

from __future__ import annotations

from ryact import create_element
from ryact_dom.dom import Container, ElementNode, SyntheticEvent
from ryact_dom.root import create_root


def _host(c: Container) -> ElementNode:
    h = c.root.children[0]
    assert isinstance(h, ElementNode)
    return h


def _find_child(root: ElementNode, *, cls: str | None = None) -> ElementNode:
    for ch in root.children:
        if not isinstance(ch, ElementNode):
            continue
        if cls is None:
            return ch
        if ch.props.get("class") == cls or ch.props.get("className") == cls:
            return ch
    raise AssertionError("child not found")


def _assert_bubbles(*, react_event: str, dispatch_type: str, host_tag: str, expect_parent: bool) -> None:
    log: list[str] = []

    def on_child(_e: SyntheticEvent) -> None:
        log.append("child")

    def on_parent(_e: SyntheticEvent) -> None:
        log.append("parent")

    c = Container()
    r = create_root(c)
    parent_props = {react_event: on_parent}
    child_props = {react_event: on_child}
    r.render(
        create_element(
            host_tag,
            parent_props,
            create_element(host_tag, child_props, className="child"),
        )
    )
    parent = _host(c)
    child = _find_child(parent, cls="child")
    child.dispatch_event(dispatch_type)
    if expect_parent:
        assert log == ["child", "parent"]
    else:
        assert log == ["child"]


def _assert_bubbles_void_child(*, react_event: str, dispatch_type: str, void_tag: str) -> None:
    log: list[str] = []

    def on_child(_e: SyntheticEvent) -> None:
        log.append("child")

    def on_parent(_e: SyntheticEvent) -> None:
        log.append("parent")

    c = Container()
    r = create_root(c)
    r.render(
        create_element(
            "div",
            {react_event: on_parent},
            create_element(void_tag, {react_event: on_child}),
        )
    )
    parent = _host(c)
    child = parent.children[0]
    assert isinstance(child, ElementNode)
    child.dispatch_event(dispatch_type)
    assert log == ["child", "parent"]




def _assert_bubbles_nested(
    *, react_event: str, dispatch_type: str, parent_tag: str, child_tag: str
) -> None:
    log: list[str] = []

    def on_child(_e: SyntheticEvent) -> None:
        log.append("child")

    def on_parent(_e: SyntheticEvent) -> None:
        log.append("parent")

    c = Container()
    r = create_root(c)
    r.render(
        create_element(
            parent_tag,
            {react_event: on_parent},
            create_element(child_tag, {react_event: on_child, "className": "child"}),
        )
    )
    parent = _host(c)
    child = _find_child(parent, cls="child")
    child.dispatch_event(dispatch_type)
    assert log == ["child", "parent"]


def _assert_enter_leave(*, enter_prop: str, leave_prop: str, over_type: str, out_type: str) -> None:
    log: list[str] = []
    c = Container()
    r = create_root(c)
    r.render(
        create_element(
            "div",
            {
                enter_prop: lambda _e: log.append("parent_enter"),
                leave_prop: lambda _e: log.append("parent_leave"),
            },
            create_element(
                "div",
                {
                    enter_prop: lambda _e: log.append("child_enter"),
                    leave_prop: lambda _e: log.append("child_leave"),
                    "className": "child",
                },
            ),
        )
    )
    parent = _host(c)
    child = _find_child(parent, cls="child")
    child.dispatch_event(over_type)
    assert log == ["parent_enter", "child_enter"]
    log.clear()
    child.dispatch_event(out_type)
    assert log == ["child_leave", "parent_leave"]

def test_onanimationend_38c8206d() -> None:
    _assert_bubbles(react_event='onAnimationEnd', dispatch_type='animationend', host_tag='div', expect_parent=True)

def test_onanimationiteration_6c3157d6() -> None:
    _assert_bubbles(react_event='onAnimationIteration', dispatch_type='animationiteration', host_tag='div', expect_parent=True)

def test_onanimationstart_a9304289() -> None:
    _assert_bubbles(react_event='onAnimationStart', dispatch_type='animationstart', host_tag='div', expect_parent=True)

def test_onauxclick_82c97d2d() -> None:
    _assert_bubbles(react_event='onAuxClick', dispatch_type='auxclick', host_tag='div', expect_parent=True)

def test_onblur_66f4cfe9() -> None:
    _assert_bubbles_void_child(react_event="onBlur", dispatch_type="focusout", void_tag="input")

def test_onclick_f07e9843() -> None:
    _assert_bubbles(react_event='onClick', dispatch_type='click', host_tag='div', expect_parent=True)

def test_oncontextmenu_3669f1ae() -> None:
    _assert_bubbles(react_event='onContextMenu', dispatch_type='contextmenu', host_tag='div', expect_parent=True)

def test_oncopy_cb71c7bc() -> None:
    _assert_bubbles(react_event='onCopy', dispatch_type='copy', host_tag='div', expect_parent=True)

def test_oncut_2e3c04bb() -> None:
    _assert_bubbles(react_event='onCut', dispatch_type='cut', host_tag='div', expect_parent=True)

def test_ondoubleclick_5d15fe9e() -> None:
    _assert_bubbles(react_event='onDoubleClick', dispatch_type='doubleclick', host_tag='div', expect_parent=True)

def test_ondrag_be5ad2fd() -> None:
    _assert_bubbles(react_event='onDrag', dispatch_type='drag', host_tag='div', expect_parent=True)

def test_ondragend_605ae7fb() -> None:
    _assert_bubbles(react_event='onDragEnd', dispatch_type='dragend', host_tag='div', expect_parent=True)

def test_ondragenter_fb7a0646() -> None:
    _assert_bubbles(react_event='onDragEnter', dispatch_type='dragenter', host_tag='div', expect_parent=True)

def test_ondragexit_47c718a8() -> None:
    _assert_bubbles(react_event='onDragExit', dispatch_type='dragexit', host_tag='div', expect_parent=True)

def test_ondragleave_e62735ee() -> None:
    _assert_bubbles(react_event='onDragLeave', dispatch_type='dragleave', host_tag='div', expect_parent=True)

def test_ondragover_fbe02ed8() -> None:
    _assert_bubbles(react_event='onDragOver', dispatch_type='dragover', host_tag='div', expect_parent=True)

def test_ondragstart_7ad47f17() -> None:
    _assert_bubbles(react_event='onDragStart', dispatch_type='dragstart', host_tag='div', expect_parent=True)

def test_ondrop_78865276() -> None:
    _assert_bubbles(react_event='onDrop', dispatch_type='drop', host_tag='div', expect_parent=True)

def test_onfocus_339df54d() -> None:
    _assert_bubbles(react_event='onFocus', dispatch_type='focus', host_tag='div', expect_parent=True)

def test_onfullscreenchange_4562d42f() -> None:
    _assert_bubbles(react_event='onFullscreenChange', dispatch_type='fullscreenchange', host_tag='div', expect_parent=True)

def test_onfullscreenerror_e34a9405() -> None:
    _assert_bubbles(react_event='onFullscreenError', dispatch_type='fullscreenerror', host_tag='div', expect_parent=True)

def test_ongotpointercapture_c2fd509a() -> None:
    _assert_bubbles(react_event="onGotPointerCapture", dispatch_type="gotpointercapture", host_tag="div", expect_parent=True)

def test_onkeydown_ace551aa() -> None:
    _assert_bubbles(react_event='onKeyDown', dispatch_type='keydown', host_tag='div', expect_parent=True)

def test_onkeypress_07312c11() -> None:
    _assert_bubbles(react_event='onKeyPress', dispatch_type='keypress', host_tag='div', expect_parent=True)

def test_onkeyup_24279bf8() -> None:
    _assert_bubbles(react_event='onKeyUp', dispatch_type='keyup', host_tag='div', expect_parent=True)

def test_onlostpointercapture_4e6ad61e() -> None:
    _assert_bubbles(react_event="onLostPointerCapture", dispatch_type="lostpointercapture", host_tag="div", expect_parent=True)

def test_onmousedown_22ca7ab2() -> None:
    _assert_bubbles(react_event='onMouseDown', dispatch_type='mousedown', host_tag='div', expect_parent=True)

def test_onmouseout_1fd66d39() -> None:
    _assert_bubbles(react_event='onMouseOut', dispatch_type='mouseout', host_tag='div', expect_parent=True)

def test_onmouseover_cf6cad77() -> None:
    _assert_bubbles(react_event='onMouseOver', dispatch_type='mouseover', host_tag='div', expect_parent=True)

def test_onmouseup_2ffe4e70() -> None:
    _assert_bubbles(react_event='onMouseUp', dispatch_type='mouseup', host_tag='div', expect_parent=True)

def test_onpaste_3078ee3e() -> None:
    _assert_bubbles(react_event='onPaste', dispatch_type='paste', host_tag='div', expect_parent=True)

def test_onpointercancel_7665ace8() -> None:
    _assert_bubbles(react_event='onPointerCancel', dispatch_type='pointercancel', host_tag='div', expect_parent=True)

def test_onpointerdown_b453c32e() -> None:
    _assert_bubbles(react_event='onPointerDown', dispatch_type='pointerdown', host_tag='div', expect_parent=True)

def test_onpointermove_a4bdf6f3() -> None:
    _assert_bubbles(react_event='onPointerMove', dispatch_type='pointermove', host_tag='div', expect_parent=True)

def test_onpointerout_1740288d() -> None:
    _assert_bubbles(react_event='onPointerOut', dispatch_type='pointerout', host_tag='div', expect_parent=True)

def test_onpointerover_143be4eb() -> None:
    _assert_bubbles(react_event='onPointerOver', dispatch_type='pointerover', host_tag='div', expect_parent=True)

def test_onpointerup_717ce627() -> None:
    _assert_bubbles(react_event='onPointerUp', dispatch_type='pointerup', host_tag='div', expect_parent=True)

def test_onreset_b9e58a3a() -> None:
    _assert_bubbles(react_event='onReset', dispatch_type='reset', host_tag='div', expect_parent=True)

def test_onsubmit_1b55a50b() -> None:
    _assert_bubbles(react_event='onSubmit', dispatch_type='submit', host_tag='div', expect_parent=True)

def test_ontouchcancel_8f5abb4b() -> None:
    _assert_bubbles(react_event='onTouchCancel', dispatch_type='touchcancel', host_tag='div', expect_parent=True)

def test_ontouchend_4a55108f() -> None:
    _assert_bubbles(react_event='onTouchEnd', dispatch_type='touchend', host_tag='div', expect_parent=True)

def test_ontouchmove_b52c2d2c() -> None:
    _assert_bubbles(react_event='onTouchMove', dispatch_type='touchmove', host_tag='div', expect_parent=True)

def test_ontouchstart_25789263() -> None:
    _assert_bubbles(react_event='onTouchStart', dispatch_type='touchstart', host_tag='div', expect_parent=True)

def test_ontransitioncancel_1d044363() -> None:
    _assert_bubbles(react_event='onTransitionCancel', dispatch_type='transitioncancel', host_tag='div', expect_parent=True)

def test_ontransitionend_5792a8d7() -> None:
    _assert_bubbles(react_event='onTransitionEnd', dispatch_type='transitionend', host_tag='div', expect_parent=True)

def test_ontransitionrun_8b6e5551() -> None:
    _assert_bubbles(react_event='onTransitionRun', dispatch_type='transitionrun', host_tag='div', expect_parent=True)

def test_ontransitionstart_cc2b9191() -> None:
    _assert_bubbles(react_event='onTransitionStart', dispatch_type='transitionstart', host_tag='div', expect_parent=True)

def test_onwheel_6d2e1a41() -> None:
    _assert_bubbles(react_event='onWheel', dispatch_type='wheel', host_tag='div', expect_parent=True)

def test_onmouseenterandonmouseleave_06933522() -> None:
    _assert_enter_leave(enter_prop='onMouseEnter', leave_prop='onMouseLeave', over_type='mouseover', out_type='mouseout')

def test_onpointerenterandonpointerleave_b20c2ea2() -> None:
    _assert_enter_leave(enter_prop='onPointerEnter', leave_prop='onPointerLeave', over_type='pointerover', out_type='pointerout')

def test_onabort_ed8cf659() -> None:
    _assert_bubbles(react_event='onAbort', dispatch_type='abort', host_tag='div', expect_parent=True)

def test_onbeforetoggledialogapi_cfa24353() -> None:
    _assert_bubbles(react_event='onBeforeToggle', dispatch_type='beforetoggle', host_tag='dialog', expect_parent=True)

def test_onbeforetogglepopoverapi_dcdff52f() -> None:
    _assert_bubbles(react_event='onBeforeToggle', dispatch_type='beforetoggle', host_tag='div', expect_parent=True)

def test_oncancel_e8c88458() -> None:
    _assert_bubbles(react_event='onCancel', dispatch_type='cancel', host_tag='div', expect_parent=True)

def test_oncanplay_58ebaced() -> None:
    _assert_bubbles_nested(react_event='onCanPlay', dispatch_type='canplay', parent_tag='div', child_tag='video')

def test_oncanplaythrough_9bb05308() -> None:
    _assert_bubbles_nested(react_event='onCanPlayThrough', dispatch_type='canplaythrough', parent_tag='div', child_tag='video')

def test_onclose_0eefee2c() -> None:
    _assert_bubbles(react_event='onClose', dispatch_type='close', host_tag='div', expect_parent=True)

def test_ondurationchange_5c597dca() -> None:
    _assert_bubbles_nested(react_event='onDurationChange', dispatch_type='durationchange', parent_tag='div', child_tag='video')

def test_onemptied_97aff7aa() -> None:
    _assert_bubbles_nested(react_event='onEmptied', dispatch_type='emptied', parent_tag='div', child_tag='video')

def test_onencrypted_8e617f70() -> None:
    _assert_bubbles_nested(react_event='onEncrypted', dispatch_type='encrypted', parent_tag='div', child_tag='video')

def test_onended_4c2ea87b() -> None:
    _assert_bubbles_nested(react_event='onEnded', dispatch_type='ended', parent_tag='div', child_tag='video')

def test_onerror_c4bfe649() -> None:
    _assert_bubbles_nested(react_event='onError', dispatch_type='error', parent_tag='div', child_tag='video')

def test_oninvalid_05bd1ece() -> None:
    _assert_bubbles(react_event='onInvalid', dispatch_type='invalid', host_tag='div', expect_parent=True)

def test_onload_6da03d0d() -> None:
    _assert_bubbles_nested(react_event='onLoad', dispatch_type='load', parent_tag='div', child_tag='embed')

def test_onloadeddata_cc986256() -> None:
    _assert_bubbles_nested(react_event='onLoadedData', dispatch_type='loadeddata', parent_tag='div', child_tag='video')

def test_onloadedmetadata_24c9af8c() -> None:
    _assert_bubbles_nested(react_event='onLoadedMetadata', dispatch_type='loadedmetadata', parent_tag='div', child_tag='video')

def test_onloadstart_f274e16c() -> None:
    _assert_bubbles_nested(react_event='onLoadStart', dispatch_type='loadstart', parent_tag='div', child_tag='video')

def test_onpause_12402678() -> None:
    _assert_bubbles_nested(react_event='onPause', dispatch_type='pause', parent_tag='div', child_tag='video')

def test_onplay_92559c43() -> None:
    _assert_bubbles_nested(react_event='onPlay', dispatch_type='play', parent_tag='div', child_tag='video')

def test_onplaying_6d01499d() -> None:
    _assert_bubbles_nested(react_event='onPlaying', dispatch_type='playing', parent_tag='div', child_tag='video')

def test_onprogress_2cfa787d() -> None:
    _assert_bubbles_nested(react_event='onProgress', dispatch_type='progress', parent_tag='div', child_tag='video')

def test_onratechange_79e0086a() -> None:
    _assert_bubbles_nested(react_event='onRateChange', dispatch_type='ratechange', parent_tag='div', child_tag='video')

def test_onresize_597ec206() -> None:
    _assert_bubbles_nested(react_event="onResize", dispatch_type="resize", parent_tag="div", child_tag="video")

def test_onseeked_42b250e8() -> None:
    _assert_bubbles_nested(react_event='onSeeked', dispatch_type='seeked', parent_tag='div', child_tag='video')

def test_onseeking_6e1b7e98() -> None:
    _assert_bubbles_nested(react_event='onSeeking', dispatch_type='seeking', parent_tag='div', child_tag='video')

def test_onstalled_bb99fed7() -> None:
    _assert_bubbles_nested(react_event='onStalled', dispatch_type='stalled', parent_tag='div', child_tag='video')

def test_onsuspend_65e931c6() -> None:
    _assert_bubbles_nested(react_event='onSuspend', dispatch_type='suspend', parent_tag='div', child_tag='video')

def test_ontimeupdate_fe40ce02() -> None:
    _assert_bubbles_nested(react_event='onTimeUpdate', dispatch_type='timeupdate', parent_tag='div', child_tag='video')

def test_ontoggle_b908647d() -> None:
    _assert_bubbles(react_event='onToggle', dispatch_type='toggle', host_tag='div', expect_parent=True)

def test_ontoggledialogapi_e6e88a37() -> None:
    _assert_bubbles(react_event='onToggle', dispatch_type='toggle', host_tag='dialog', expect_parent=True)

def test_ontogglepopoverapi_d94c13d6() -> None:
    _assert_bubbles(react_event='onToggle', dispatch_type='toggle', host_tag='div', expect_parent=True)

def test_onvolumechange_68987be7() -> None:
    _assert_bubbles_nested(react_event='onVolumeChange', dispatch_type='volumechange', parent_tag='div', child_tag='video')

def test_onwaiting_b9a37054() -> None:
    _assert_bubbles_nested(react_event='onWaiting', dispatch_type='waiting', parent_tag='div', child_tag='video')

def test_onscroll_60d5a51d() -> None:
    _assert_bubbles(react_event='onScroll', dispatch_type='scroll', host_tag='div', expect_parent=False)

def test_onscrollend_d12991ad() -> None:
    _assert_bubbles(react_event='onScrollEnd', dispatch_type='scrollend', host_tag='div', expect_parent=False)

def test_onbeforeinput_36bbce6a() -> None:
    _assert_bubbles(react_event='onBeforeInput', dispatch_type='beforeinput', host_tag='div', expect_parent=True)

def test_onchange_4e3abff5() -> None:
    _assert_bubbles_void_child(react_event='onChange', dispatch_type='change', void_tag='input')

def test_oncompositionend_d6265fbc() -> None:
    _assert_bubbles(react_event='onCompositionEnd', dispatch_type='compositionend', host_tag='div', expect_parent=True)

def test_oncompositionstart_0fc93d83() -> None:
    _assert_bubbles(react_event='onCompositionStart', dispatch_type='compositionstart', host_tag='div', expect_parent=True)

def test_oncompositionupdate_ad6c838f() -> None:
    _assert_bubbles(react_event='onCompositionUpdate', dispatch_type='compositionupdate', host_tag='div', expect_parent=True)

def test_onselect_bf74ca46() -> None:
    _assert_bubbles_void_child(react_event='onSelect', dispatch_type='select', void_tag='input')

