from __future__ import annotations

from typing import Any

from ryact import (
    Component,
    create_element,
    get_legacy_context,
    memo,
    start_transition,
    use,
    use_state,
    use_transition,
)
from ryact.concurrent import Thenable, lazy
from ryact.context import context_provider, create_context
from ryact_testkit import WarningCapture, act_call, create_noop_root, set_act_environment_enabled


def _span(text: str, *, key: str | None = None) -> Any:
    p: dict[str, Any] = {"text": text}
    if key is not None:
        p["key"] = key
    return create_element("span", p)


class _UncachedThenable:
    """Like a fresh Promise.resolve — not :class:`Thenable`; triggers DEV uncached warnings."""

    __slots__ = ("_status", "_value")

    def __init__(self, value: str) -> None:
        self._status = "fulfilled"
        self._value = value

    @property
    def status(self) -> str:
        return self._status

    @property
    def value(self) -> str:
        return self._value

    def then(self, cb: Any, _on_err: Any = None) -> None:
        cb()


def test_unwrap_uncached_promises_with_legacy_context_function_and_memo() -> None:
    # Upstream: ReactUse-test.js — "unwrap uncached promises in component that accesses legacy context"
    class LegacyProvider(Component):
        childContextTypes = {"legacyContext": None}

        def getChildContext(self) -> dict[str, str]:  # noqa: N802
            return {"legacyContext": "Async"}

        def render(self) -> Any:
            ch = self.props.get("children")
            if isinstance(ch, tuple):
                return create_element("div", {"children": ch})
            return ch

    def Async(**props: Any) -> Any:
        label = props["label"]
        lc = get_legacy_context().get("legacyContext", "")
        t = _UncachedThenable(f"{lc} ({label})")
        return _span(str(use(t)), key=str(label))

    Async.contextTypes = {"legacyContext": None}  # type: ignore[attr-defined]

    M = memo(Async)

    def App() -> Any:
        return create_element(
            LegacyProvider,
            {
                "children": (
                    create_element(Async, {"label": "function component", "key": "fn"}),
                    create_element(M, {"label": "memo component", "key": "mem"}),
                )
            },
        )

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with WarningCapture() as wc:
            act_call(
                lambda: start_transition(lambda: root.render(create_element(App))),
                flush=root.flush,
            )
        snap = root.get_children_snapshot()
        assert isinstance(snap, dict) and snap.get("type") == "div"
        children = snap.get("children") or []
        texts = sorted(str(c["props"]["text"]) for c in children if isinstance(c, dict))
        assert texts == [
            "Async (function component)",
            "Async (memo component)",
        ]
        uncached = sum(1 for m in wc.messages if "uncached promise" in m.lower())
        assert uncached == 2
    finally:
        set_act_environment_enabled(False)


def test_using_fresh_thenables_in_one_transition_composes() -> None:
    # Upstream: ReactUse-test.js — "using a promise that's not cached between attempts"
    def Async() -> Any:
        return _span(
            str(use(_UncachedThenable("A"))) + str(use(_UncachedThenable("B"))) + str(use(_UncachedThenable("C")))
        )

    def App() -> Any:
        return create_element(Async)

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with WarningCapture() as wc:
            act_call(
                lambda: start_transition(lambda: root.render(create_element(App))),
                flush=root.flush,
            )
        assert root.get_children_snapshot()["props"]["text"] == "ABC"
        assert len(wc.records) == 3
        for r in wc.records:
            assert "uncached promise" in str(r.message).lower()
    finally:
        set_act_environment_enabled(False)


def test_interrupt_while_lazy_pending_flush_sync_reads_latest_context() -> None:
    # Upstream: ReactUse-test.js — "interrupting while yielded should reset contexts"
    Cx = create_context("")
    mod_then = Thenable()
    L = lazy(lambda: mod_then)

    def Read(**_: Any) -> Any:
        return _span(str(use(Cx)), key="r")

    def LazyDefault(**_: Any) -> Any:
        return create_element(Read)

    def App(**props: Any) -> Any:
        outer = str(props.get("text", ""))
        return context_provider(
            Cx,
            outer,
            create_element(
                "__suspense__",
                {
                    "fallback": _span("fb", key="fb"),
                    "children": (create_element(L, {"key": "lz"}),),
                },
            ),
        )

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        act_call(
            lambda: start_transition(lambda: root.render(create_element(App, {"text": "Hello "}))),
            flush=root.flush,
        )
        assert root.get_children_snapshot()["props"]["text"] == "fb"

        def resume_and_sync() -> None:
            mod_then.resolve({"default": LazyDefault})
            root.flush_sync(lambda: root.render(create_element(App, {"text": "world!"})))

        act_call(resume_and_sync, flush=root.flush)
        assert root.get_children_snapshot()["props"]["text"] == "world!"
    finally:
        set_act_environment_enabled(False)


def test_flush_sync_rerender_reads_latest_context() -> None:
    # Behavioral subset of upstream ReactUse — "interrupting while yielded should reset contexts":
    # a sync priority render must not leave a stale Context._current_value from a prior tree.
    Cx = create_context("")

    def Read(**_: Any) -> Any:
        return _span(str(use(Cx)), key="r")

    def App(**props: Any) -> Any:
        return context_provider(Cx, str(props.get("text", "")), create_element(Read))

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        act_call(lambda: root.render(create_element(App, {"text": "Hello "})), flush=root.flush)
        assert root.get_children_snapshot()["props"]["text"] == "Hello "
        act_call(
            lambda: root.flush_sync(lambda: root.render(create_element(App, {"text": "world!"}))),
            flush=root.flush,
        )
        assert root.get_children_snapshot()["props"]["text"] == "world!"
    finally:
        set_act_environment_enabled(False)


def test_interleaved_transition_does_not_stay_suspended_on_skipped_work() -> None:
    # Upstream: ReactUse-test.js — "does not suspend indefinitely if an interleaved update was skipped"
    logs: list[str] = []
    pending_by_text: dict[str, Thenable] = {}

    def async_text(text: str) -> Thenable:
        logs.append(f"Async text requested [{text}]")
        if text not in pending_by_text:
            pending_by_text[text] = Thenable()
        return pending_by_text[text]

    bag: dict[str, Any] = {}

    def Child(**props: Any) -> Any:
        if props.get("childShouldSuspend"):
            return _span(str(use(async_text("Will never resolve"))), key="sus")
        logs.append("Child")
        return _span("Child", key="ok")

    def Parent() -> Any:
        show_child, set_show_child = use_state(True)
        child_suspend, set_child_suspend = use_state(False)
        _, start = use_transition()
        logs.append(f"childShouldSuspend: {child_suspend}, showChild: {show_child}")
        bag["start"] = start
        bag["set_show"] = set_show_child
        bag["set_suspend"] = set_child_suspend
        if not show_child:
            return _span("(empty)", key="empty")
        return create_element(
            "__suspense__",
            {
                "fallback": _span("Loading", key="ld"),
                "children": (create_element(Child, {"childShouldSuspend": child_suspend}),),
            },
        )

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        act_call(lambda: root.render(create_element(Parent)), flush=root.flush)
        assert logs[:2] == [
            "childShouldSuspend: False, showChild: True",
            "Child",
        ]
        logs.clear()

        act_call(lambda: bag["start"](lambda: bag["set_suspend"](True)), flush=root.flush)
        assert "Async text requested [Will never resolve]" in logs

        act_call(lambda: bag["start"](lambda: bag["set_show"](False)), flush=root.flush)
        assert root.get_children_snapshot()["props"]["text"] == "(empty)"
    finally:
        set_act_environment_enabled(False)
