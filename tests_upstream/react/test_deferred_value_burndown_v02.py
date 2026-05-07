from __future__ import annotations

from typing import Any

from ryact import create_element, use_deferred_value, use_state
from ryact.concurrent import start_transition
from ryact_testkit import create_noop_root


def test_supports_initialvalue_argument_static_literals() -> None:
    # Upstream: ReactDeferredValue-test.js — "supports initialValue argument"
    def App() -> object:
        text = use_deferred_value("Final", "Initial")
        return create_element("div", {"text": text})

    root = create_noop_root()
    root.render(create_element(App))
    c0 = root.container.last_committed
    assert c0 is not None
    assert c0["props"]["text"] == "Initial"

    root.flush()
    c1 = root.container.last_committed
    assert c1 is not None
    assert c1["props"]["text"] == "Final"


def test_regression_urgent_update_reuses_previous_deferred_not_initial() -> None:
    # Upstream: ReactDeferredValue-test.js
    # "regression test: during urgent update, reuse previous value, not initial value"
    def Child(*, value: int) -> object:
        val, set_val = use_state(value)
        if val != value:
            set_val(value)
        deferred = use_deferred_value(val)
        return create_element("div", {"orig": val, "def": deferred})

    root = create_noop_root()
    root.render(create_element(Child, {"value": 1}))
    root.flush()
    c = root.container.last_committed
    assert c is not None
    assert c["props"]["orig"] == 1
    assert c["props"]["def"] == 1

    start_transition(lambda: root.render(create_element(Child, {"value": 2})))
    root.flush()
    c2 = root.container.last_committed
    assert c2 is not None
    assert c2["props"]["orig"] == 2
    assert c2["props"]["def"] == 2

    # Urgent update commits immediately for `orig` while `def` lags (separate LOW commit), like
    # upstream waitForPaint(['Original: 3']) before Deferred catches up.
    root.render(create_element(Child, {"value": 3}))
    c_urgent = root.container.last_committed
    assert c_urgent is not None
    assert c_urgent["props"]["orig"] == 3
    assert c_urgent["props"]["def"] == 2

    root.flush()
    c_catchup = root.container.last_committed
    assert c_catchup is not None
    assert c_catchup["props"]["orig"] == 3
    assert c_catchup["props"]["def"] == 3


def test_works_with_render_phase_state_sync_like_upstream() -> None:
    # Upstream: ReactDeferredValue-test.js — "works if there's a render phase update"
    def Child(*, value: int) -> object:
        val, set_val = use_state(None)
        if val != value:
            set_val(value)
        deferred = use_deferred_value(val)
        return create_element("div", {"orig": val, "def": deferred})

    root = create_noop_root()
    root.render(create_element(Child, {"value": 1}))
    root.flush()
    c0 = root.container.last_committed
    assert c0 is not None
    assert c0["props"]["orig"] == 1
    assert c0["props"]["def"] == 1

    root.render(create_element(Child, {"value": 2}))
    c_urgent = root.container.last_committed
    assert c_urgent is not None
    assert c_urgent["props"]["orig"] == 2
    assert c_urgent["props"]["def"] == 1

    root.flush()
    c1 = root.container.last_committed
    assert c1 is not None
    assert c1["props"]["orig"] == 2
    assert c1["props"]["def"] == 2

    start_transition(lambda: root.render(create_element(Child, {"value": 3})))
    root.flush()
    c2 = root.container.last_committed
    assert c2 is not None
    assert c2["props"]["orig"] == 3
    assert c2["props"]["def"] == 3


def _collect_prop(node: object, key: str) -> list[Any]:
    out: list[Any] = []
    if not isinstance(node, dict):
        return out
    props = node.get("props")
    if isinstance(props, dict) and key in props:
        out.append(props[key])
    for ch in node.get("children") or []:
        out.extend(_collect_prop(ch, key))
    return out


def test_nested_use_deferred_value_skips_inner_initial_preview_on_catch_up() -> None:
    # Upstream: ReactDeferredValue-test.js — multi-level deferral without Suspense:
    # inner useDeferredValue(initialValue) should not show inner preview when mounted
    # during a parent LOW catch-up (avoids preview waterfall).
    def Inner() -> object:
        text = use_deferred_value("Content", "Preview")
        return create_element("span", {"inner": text})

    def App() -> object:
        show = use_deferred_value(True, False)
        if not show:
            return create_element("div", {"phase": "app_gate"})
        return create_element("div", {"phase": "app_ready"}, create_element(Inner))

    root = create_noop_root()
    root.render(create_element(App))
    c0 = root.container.last_committed
    assert c0 is not None
    assert c0["props"]["phase"] == "app_gate"

    inner_during = []
    for snap in root.container.commits:
        inner_during.extend(_collect_prop(snap, "inner"))
    assert "Preview" not in inner_during

    root.flush()
    c1 = root.container.last_committed
    assert c1 is not None
    assert c1["props"]["phase"] == "app_ready"
    inner_after = _collect_prop(c1, "inner")
    assert inner_after == ["Content"]

    inner_all = []
    for snap in root.container.commits:
        inner_all.extend(_collect_prop(snap, "inner"))
    assert "Preview" not in inner_all
    assert inner_all[-1] == "Content"
