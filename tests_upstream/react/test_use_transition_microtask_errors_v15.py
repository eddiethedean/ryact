from __future__ import annotations

from typing import Any

import pytest

from ryact import create_element, use_state, use_transition, use
from ryact.concurrent import Thenable
from ryact_testkit import (
    act_call,
    create_noop_root,
    queue_microtask,
    set_act_environment_enabled,
)


def _span(text: str, *, key: str | None = None) -> Any:
    p: dict[str, Any] = {"text": text}
    if key is not None:
        p["key"] = key
    return create_element("span", p)


def _suspense(fb: Any, child: Any, *, key: str | None = None) -> Any:
    props: dict[str, Any] = {"fallback": fb, "children": (child,)}
    if key is not None:
        props["key"] = key
    return create_element("__suspense__", props)


def test_suspended_fiber_ping_in_microtask_retries_without_extra_stack_magic() -> None:
    # Upstream: ReactUse-test.js
    # "if suspended fiber is pinged in a microtask, retry immediately without unwinding the stack"
    t = Thenable()

    def App() -> Any:
        v = use(t)
        return _span(str(v), key="c")

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        act_call(
            lambda: root.render(_suspense(_span("fb", key="fb"), create_element(App, {"key": "a"}))),
            flush=root.flush,
        )
        assert root.get_children_snapshot()["props"]["text"] == "fb"

        def schedule_resolve() -> None:
            queue_microtask(lambda: t.resolve("ping"))

        act_call(schedule_resolve, flush=root.flush, drain_microtasks=5)
        assert root.get_children_snapshot()["props"]["text"] == "ping"
    finally:
        set_act_environment_enabled(False)


def test_suspended_fiber_ping_in_microtask_does_not_block_transition_from_completing() -> None:
    # Upstream: ReactUse-test.js
    # "if suspended fiber is pinged in a microtask, it does not block a transition from completing"
    t = Thenable()
    bag: dict[str, Any] = {}

    def Inner() -> Any:
        return _span(str(use(t)), key="in")

    def App() -> Any:
        pending, start = use_transition()
        show, set_show = use_state(False)
        bag["start"] = start
        bag["set_show"] = set_show
        if not show:
            return _span(f"idle:{pending}", key="idle")
        return create_element(
            "div",
            {
                "key": "root",
                "children": [
                    _span(f"pend:{pending}", key="p"),
                    _suspense(_span("fb", key="fb"), create_element(Inner, {"key": "i"}), key="s"),
                ],
            },
        )

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        act_call(lambda: root.render(create_element(App)), flush=root.flush)
        assert "idle:False" in str(root.get_children_snapshot())

        def kick_transition_and_resolve() -> None:
            bag["start"](lambda: bag["set_show"](True))
            queue_microtask(lambda: t.resolve("z"))

        act_call(kick_transition_and_resolve, flush=root.flush, drain_microtasks=8)
        snap = root.get_children_snapshot()
        assert snap["type"] == "div"
        texts = sorted(
            str(c["props"]["text"]) for c in (snap.get("children") or []) if isinstance(c, dict)
        )
        assert "pend:False" in texts
        assert "z" in texts
    finally:
        set_act_environment_enabled(False)


def test_during_transition_can_unwrap_async_without_cache() -> None:
    # Upstream: ReactUse-test.js
    # "during a transition, can unwrap async operations even if nothing is cached"
    t = Thenable()
    bag: dict[str, Any] = {}

    def Reader() -> Any:
        return _span(str(use(t)), key="r")

    def App() -> Any:
        pending, start = use_transition()
        on, set_on = use_state(False)
        bag["start"] = start
        bag["set_on"] = set_on
        if not on:
            return _span(f"off:{pending}", key="off")
        return _suspense(_span("loading", key="ld"), create_element(Reader, {"key": "rd"}), key="sus")

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        act_call(lambda: root.render(create_element(App)), flush=root.flush)
        assert root.get_children_snapshot()["props"]["text"] == "off:False"

        act_call(lambda: bag["start"](lambda: bag["set_on"](True)), flush=root.flush)
        assert root.get_children_snapshot()["props"]["text"] == "loading"

        act_call(lambda: t.resolve("uncached"), flush=root.flush)
        assert root.get_children_snapshot()["props"]["text"] == "uncached"
    finally:
        set_act_environment_enabled(False)


def test_new_suspense_boundary_shows_fallback_even_during_transition() -> None:
    # Upstream: ReactUse-test.js
    # "does not prevent a Suspense fallback from showing if it's a new boundary, even during a transition"
    t = Thenable()
    bag: dict[str, Any] = {}

    def Leaf() -> Any:
        return _span(str(use(t)), key="lf")

    def App() -> Any:
        pending, start = use_transition()
        gen, set_gen = use_state(0)
        bag["start"] = start
        bag["set_gen"] = set_gen
        if gen == 0:
            return _span(f"boot:{pending}", key="b")

        return _suspense(
            _span("new-fb", key="nfb"),
            create_element(Leaf, {"key": "leaf"}),
            key="new-sus",
        )

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        act_call(lambda: root.render(create_element(App)), flush=root.flush)
        assert root.get_children_snapshot()["props"]["text"] == "boot:False"

        act_call(lambda: bag["start"](lambda: bag["set_gen"](1)), flush=root.flush)
        assert root.get_children_snapshot()["props"]["text"] == "new-fb"

        act_call(lambda: t.resolve("leaf"), flush=root.flush)
        assert root.get_children_snapshot()["props"]["text"] == "leaf"
    finally:
        set_act_environment_enabled(False)


def test_erroring_same_component_as_uncached_promise_does_not_infinite_loop() -> None:
    # Upstream: ReactUse-test.js
    # "erroring in the same component as an uncached promise does not result in an infinite loop"
    t = Thenable()
    t.resolve("x")
    renders: list[int] = [0]

    def App() -> Any:
        renders[0] += 1
        if renders[0] > 40:
            pytest.fail("too many renders — possible infinite loop")
        _ = use(t)
        raise RuntimeError("same-render error")

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with pytest.raises(RuntimeError, match="same-render error"):
            act_call(
                lambda: root.render(_suspense(_span("fb"), create_element(App))),
                flush=root.flush,
            )
        assert renders[0] <= 5
    finally:
        set_act_environment_enabled(False)
