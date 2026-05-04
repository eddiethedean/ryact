from __future__ import annotations

from typing import Any

from ryact import create_element, use_state, use_transition, use
from ryact.concurrent import Thenable
from ryact_testkit import create_noop_root


def _span(text: str, *, key: str | None = None) -> Any:
    p: dict[str, Any] = {"text": text}
    if key is not None:
        p["key"] = key
    return create_element("span", p)


def _texts(snap: Any) -> list[str]:
    if not isinstance(snap, dict):
        return []
    out: list[str] = []
    if snap.get("type") == "span" and isinstance(snap.get("props"), dict):
        t = snap["props"].get("text")
        if t is not None:
            out.append(str(t))
    for c in snap.get("children") or []:
        out.extend(_texts(c))
    return out


def test_when_waiting_for_data_fresh_update_triggers_restart() -> None:
    # Upstream: ReactUse-test.js — "when waiting for data to resolve, a fresh update will trigger a restart"
    t = Thenable()
    bag: dict[str, Any] = {}

    def Child(*, version: int) -> Any:
        _ = version
        v = use(t)
        return _span(f"child:{v}", key="c")

    def App() -> Any:
        n, set_n = use_state(0)
        bag["set_n"] = set_n
        return create_element(
            "__suspense__",
            {
                "key": "s",
                "fallback": _span(f"fb:{n}", key="fb"),
                "children": (create_element(Child, {"key": "ch", "version": n}),),
            },
        )

    root = create_noop_root()
    root.render(create_element(App))
    root.flush()
    assert "fb:0" in _texts(root.get_children_snapshot())

    bag["set_n"](1)
    root.flush()
    # Still suspended; parent re-render should show bumped fallback label.
    assert "fb:1" in _texts(root.get_children_snapshot())

    t.resolve("x")
    root.flush()
    assert "child:x" in _texts(root.get_children_snapshot())


def test_when_waiting_update_on_different_root_does_not_drop_work() -> None:
    # Upstream: ReactUse-test.js
    # "when waiting for data to resolve, an update on a different root does not cause work to be dropped"
    t1 = Thenable()
    t2 = Thenable()

    def C1() -> Any:
        return _span(str(use(t1)), key="c1")

    def C2() -> Any:
        return _span(str(use(t2)), key="c2")

    r1 = create_noop_root()
    r2 = create_noop_root()
    r1.render(
        create_element(
            "__suspense__",
            {"key": "s1", "fallback": _span("l1", key="f1"), "children": (create_element(C1, {"key": "k1"}),)},
        )
    )
    r2.render(
        create_element(
            "__suspense__",
            {"key": "s2", "fallback": _span("l2", key="f2"), "children": (create_element(C2, {"key": "k2"}),)},
        )
    )
    r1.flush()
    r2.flush()
    assert r1.get_children_snapshot()["props"]["text"] == "l1"
    assert r2.get_children_snapshot()["props"]["text"] == "l2"

    t1.resolve("a")
    r1.flush()
    assert "a" in _texts(r1.get_children_snapshot())
    r2.flush()
    assert r2.get_children_snapshot()["props"]["text"] == "l2"

    t2.resolve("b")
    r2.flush()
    assert "b" in _texts(r2.get_children_snapshot())
    r1.flush()
    assert "a" in _texts(r1.get_children_snapshot())


def test_regression_pending_not_stuck_after_use_suspends_use_before_other_hooks() -> None:
    # Upstream: ReactUse-test.js
    # "regression: does not get stuck in pending state after `use` suspends (when `use` comes before all hooks)"
    t = Thenable()
    bag: dict[str, Any] = {}

    def Child() -> Any:
        use(t)
        _s, _ = use_state(0)
        return _span("ready", key="r")

    def App() -> Any:
        pending, start = use_transition()
        show, set_show = use_state(False)
        bag["start"] = start
        bag["set_show"] = set_show
        kids: list[Any] = [_span(f"pend:{pending}", key="p")]
        if show:
            kids.append(
                create_element(
                    "__suspense__",
                    {
                        "key": "s",
                        "fallback": _span("fb", key="fb"),
                        "children": (create_element(Child, {"key": "c"}),),
                    },
                )
            )
        return create_element("div", {"key": "root", "children": kids})

    root = create_noop_root()
    root.render(create_element(App))
    root.flush()
    assert "pend:False" in _texts(root.get_children_snapshot())

    bag["start"](lambda: bag["set_show"](True))
    root.flush()
    txts = _texts(root.get_children_snapshot())
    assert "fb" in txts
    assert "pend:False" in txts

    t.resolve("ok")
    root.flush()
    assert "ready" in _texts(root.get_children_snapshot())
    assert "pend:False" in _texts(root.get_children_snapshot())


def test_regression_pending_not_stuck_after_use_suspends_use_in_middle_of_hook_list() -> None:
    # Upstream: ReactUse-test.js
    # "regression: does not get stuck in pending state after `use` suspends (when `use` in in the middle of hook list)"
    t = Thenable()
    bag: dict[str, Any] = {}

    def Child() -> Any:
        _s, _ = use_state(0)
        use(t)
        return _span("ready", key="r")

    def App() -> Any:
        pending, start = use_transition()
        show, set_show = use_state(False)
        bag["start"] = start
        bag["set_show"] = set_show
        kids: list[Any] = [_span(f"pend:{pending}", key="p")]
        if show:
            kids.append(
                create_element(
                    "__suspense__",
                    {
                        "key": "s",
                        "fallback": _span("fb", key="fb"),
                        "children": (create_element(Child, {"key": "c"}),),
                    },
                )
            )
        return create_element("div", {"key": "root", "children": kids})

    root = create_noop_root()
    root.render(create_element(App))
    root.flush()
    assert "pend:False" in _texts(root.get_children_snapshot())

    bag["start"](lambda: bag["set_show"](True))
    root.flush()
    txts = _texts(root.get_children_snapshot())
    assert "fb" in txts
    assert "pend:False" in txts

    t.resolve("ok")
    root.flush()
    assert "ready" in _texts(root.get_children_snapshot())
    assert "pend:False" in _texts(root.get_children_snapshot())