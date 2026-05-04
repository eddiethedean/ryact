from __future__ import annotations

from typing import Any

from ryact import create_element
from ryact.concurrent import Thenable, suspense
from ryact.hooks import use_debug_value, use_memo, use_state
from ryact.use import use
from ryact_testkit import create_noop_root


def _text(value: str) -> Any:
    return create_element("span", {"text": value})


def test_when_replaying_suspended_component_reuses_hooks_debug_value_and_state() -> None:
    # Upstream: ReactUse-test.js
    # "when replaying a suspended component, reuses the hooks computed during the previous attempt (DebugValue+State)"
    t = Thenable()
    state_inits: list[str] = []

    def App() -> Any:
        use_debug_value("dbg")
        v, _set_v = use_state(lambda: state_inits.append("init") or 123)
        _ = use(t)
        return _text(f"v={v}")

    root = create_noop_root()
    root.render(suspense(fallback=_text("loading"), children=create_element(App)))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "loading"
    assert state_inits == ["init"]

    t.resolve("ok")
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "v=123"
    assert state_inits == ["init"]


def test_when_replaying_suspended_component_reuses_hooks_memo() -> None:
    # Upstream: ReactUse-test.js
    # "when replaying a suspended component, reuses the hooks computed during the previous attempt (Memo)"
    t = Thenable()
    memo_calls: list[str] = []

    def App() -> Any:
        m = use_memo(lambda: memo_calls.append("memo") or "M", ())
        _ = use(t)
        return _text(f"m={m}")

    root = create_noop_root()
    root.render(suspense(fallback=_text("loading"), children=create_element(App)))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "loading"
    assert memo_calls == ["memo"]

    t.resolve("ok")
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "m=M"
    assert memo_calls == ["memo"]


def test_when_replaying_suspended_component_reuses_hooks_state() -> None:
    # Upstream: ReactUse-test.js
    # "when replaying a suspended component, reuses the hooks computed during the previous attempt (State)"
    t = Thenable()
    init_calls: list[str] = []

    def App() -> Any:
        v, _set_v = use_state(lambda: init_calls.append("init") or 7)
        _ = use(t)
        return _text(f"v={v}")

    root = create_noop_root()
    root.render(suspense(fallback=_text("loading"), children=create_element(App)))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "loading"
    assert init_calls == ["init"]

    t.resolve("ok")
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "v=7"
    assert init_calls == ["init"]
