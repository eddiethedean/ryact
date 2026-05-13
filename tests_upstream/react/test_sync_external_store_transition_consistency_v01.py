# Upstream-inspired: React Fiber ``pushStoreConsistencyCheck`` / transition tearing replay.
# If the external store mutates mid-render so an earlier ``useSyncExternalStore`` snapshot
# is stale, the noop renderer retries the render pass (bounded) so siblings observe a
# consistent store.
from __future__ import annotations

from typing import Any

from ryact import create_element, use_sync_external_store
from ryact.concurrent import TRANSITION_LANE, start_transition
from ryact_testkit import act, create_noop_root, set_act_environment_enabled


def test_transition_rerender_replays_when_store_tears_mid_tree() -> None:
    class Store:
        def __init__(self) -> None:
            self._v = 0
            self._subs: list[Any] = []

        def get(self) -> int:
            return self._v

        def subscribe(self, cb: Any) -> Any:
            self._subs.append(cb)

            def unsub() -> None:
                self._subs.remove(cb)

            return unsub

        def set(self, v: int) -> None:
            self._v = v
            for cb in list(self._subs):
                cb()

    store = Store()
    log: list[str] = []
    gate = {"armed": True}

    def A(**_: Any) -> Any:
        v = use_sync_external_store(store.subscribe, store.get)
        log.append(f"A{v}")
        return create_element("span", {"text": f"a{v}"})

    def B(**_: Any) -> Any:
        _ = use_sync_external_store(store.subscribe, store.get)
        if gate["armed"]:
            gate["armed"] = False
            store.set(1)
        v = store.get()
        log.append(f"B{v}")
        return create_element("span", {"text": f"b{v}"})

    def C(**_: Any) -> Any:
        v = use_sync_external_store(store.subscribe, store.get)
        log.append(f"C{v}")
        return create_element("span", {"text": f"c{v}"})

    def App(**_: Any) -> Any:
        return create_element(
            "div",
            {
                "children": [
                    create_element(A, {"key": "a"}),
                    create_element(B, {"key": "b"}),
                    create_element(C, {"key": "c"}),
                ]
            },
        )

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            start_transition(lambda: root.render(create_element(App), lane=TRANSITION_LANE))
        snap = root.get_children_snapshot()
        assert isinstance(snap, dict)
        texts = sorted(
            str(c.get("props", {}).get("text", "")) for c in (snap.get("children") or []) if isinstance(c, dict)
        )
        assert texts == ["a1", "b1", "c1"]
        assert log[-3:] == ["A1", "B1", "C1"]
    finally:
        set_act_environment_enabled(False)
