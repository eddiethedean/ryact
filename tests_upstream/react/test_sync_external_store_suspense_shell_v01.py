# Upstream: packages/react-reconciler/src/__tests__/useSyncExternalStore-test.js
# "regression: suspending in shell after synchronously patching up store mutation"
#
# Ryact noop harness: root-level `use()` suspension must be wrapped in a Suspense
# boundary (fallback None → null snapshot). Partial progress uses `yield_after_nodes`
# tuned for Shell → suspense → App → fragment → span → A → inner span.
from __future__ import annotations

from typing import Any

from ryact import create_element, use_sync_external_store
from ryact.concurrent import TRANSITION_LANE, Thenable, fragment, start_transition
from ryact.use import use
from ryact_testkit import act, create_noop_root, set_act_environment_enabled


def test_suspense_shell_after_store_mutation_and_sync_rerender() -> None:
    store_holder: dict[str, Any] = {"store": None}
    t_holder: dict[str, Any] = {"t": None}
    log: list[str] = []

    class Store:
        def __init__(self, value: str) -> None:
            self._value = value
            self._subs: list[Any] = []

        def get_snapshot(self) -> str:
            return self._value

        def subscribe(self, cb: Any) -> Any:
            self._subs.append(cb)

            def unsub() -> None:
                self._subs.remove(cb)

            return unsub

        def set(self, value: str) -> None:
            self._value = value
            for cb in list(self._subs):
                cb()

    store = Store("Initial")
    store_holder["store"] = store
    t = Thenable()
    t_holder["t"] = t

    def A(**_: Any) -> Any:
        st = store_holder["store"]
        assert st is not None
        value = use_sync_external_store(st.subscribe, st.get_snapshot)
        log.append(f"A:{value}")
        if value == "Updated":
            use(t_holder["t"])
        return create_element("span", {"text": f"A: {value}"})

    def B(**_: Any) -> Any:
        st = store_holder["store"]
        assert st is not None
        value = use_sync_external_store(st.subscribe, st.get_snapshot)
        log.append(f"B:{value}")
        return create_element("span", {"text": f"B: {value}"})

    def App(**_: Any) -> Any:
        return fragment(
            create_element("span", {"key": "sa", "children": (create_element(A),)}),
            create_element("span", {"key": "sb", "children": (create_element(B),)}),
        )

    def Shell(**_: Any) -> Any:
        return create_element(
            "__suspense__",
            {"fallback": None, "children": (create_element(App),)},
        )

    root = create_noop_root(yield_after_nodes=7)
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            start_transition(lambda: root.render(create_element(Shell), lane=TRANSITION_LANE))
        assert log == ["A:Initial"]
        assert root.get_children_snapshot() is None

        store.set("Updated")
        root.set_yield_after_nodes(0)
        with act(flush=root.flush):
            pass
        assert root.get_children_snapshot() is None

        with act(flush=root.flush):
            t.resolve()
        snap = root.get_children_snapshot()
        assert isinstance(snap, list)
        texts = []
        for outer in snap:
            assert isinstance(outer, dict)
            ch = outer.get("children") or []
            for c in ch:
                if isinstance(c, dict) and c.get("type") == "span":
                    texts.append(str(c.get("props", {}).get("text", "")))
        assert texts == ["A: Updated", "B: Updated"]
    finally:
        set_act_environment_enabled(False)
