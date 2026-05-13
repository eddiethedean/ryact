# Upstream: packages/react-reconciler/src/__tests__/useSyncExternalStore-test.js
# Same `it(...)` as "detects interleaved mutations during a concurrent read before
# layout effects fire" — forwardRef + three children + concurrent yield + interleaved
# store mutation.
#
# Ryact: the noop `yield_after_nodes` resume restarts the tree from the root on the
# next flush, so we do not observe React’s exact Scheduler log ordering (C1 alone,
# then full discard/restart). We still assert the observable guarantee: after a
# partial transition read (A0 only), an interleaved mutation commits a consistent
# trio (A1/B1/C1) with no torn snapshots in the final host tree.
from __future__ import annotations

from typing import Any

from ryact import create_element, use_sync_external_store
from ryact.concurrent import TRANSITION_LANE, start_transition
from ryact_testkit import act, create_noop_root, set_act_environment_enabled


def test_partial_transition_then_mutation_commits_consistent_siblings() -> None:
    class Store:
        def __init__(self, value: int) -> None:
            self._value = value
            self._subs: list[Any] = []

        def get_snapshot(self) -> int:
            return self._value

        def subscribe(self, cb: Any) -> Any:
            self._subs.append(cb)

            def unsub() -> None:
                self._subs.remove(cb)

            return unsub

        def set(self, value: int) -> None:
            self._value = value
            for cb in list(self._subs):
                cb()

    store = Store(0)
    log: list[str] = []

    def Child(*, label: str, **_extra: Any) -> Any:
        v = use_sync_external_store(store.subscribe, store.get_snapshot)
        log.append(f"{label}{v}")
        return create_element("span", {"text": f"{label}{v}"})

    def App(**_: Any) -> Any:
        return create_element(
            "div",
            {
                "children": [
                    create_element(Child, {"key": "a", "label": "A"}),
                    create_element(Child, {"key": "b", "label": "B"}),
                    create_element(Child, {"key": "c", "label": "C"}),
                ]
            },
        )

    root = create_noop_root(yield_after_nodes=5)
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            start_transition(lambda: root.render(create_element(App), lane=TRANSITION_LANE))
        assert log == ["A0"]

        store.set(1)
        root.set_yield_after_nodes(0)
        with act(flush=root.flush):
            pass

        snap = root.get_children_snapshot()
        assert isinstance(snap, dict)
        children = snap.get("children") or []
        texts = [str(c.get("props", {}).get("text", "")) for c in children if isinstance(c, dict)]
        assert texts == ["A1", "B1", "C1"]
        assert log[-3:] == ["A1", "B1", "C1"]
    finally:
        set_act_environment_enabled(False)
