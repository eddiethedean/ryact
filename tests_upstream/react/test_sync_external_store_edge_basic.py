from __future__ import annotations

from collections.abc import Callable

from ryact import create_element, use_insertion_effect, use_sync_external_store
from ryact_testkit import create_noop_root


class Store:
    def __init__(self, value: str) -> None:
        self._value = value
        self._subs: list[Callable[[], None]] = []

    def get_snapshot(self) -> str:
        return self._value

    def subscribe(self, cb: Callable[[], None]) -> Callable[[], None]:
        self._subs.append(cb)

        def unsub() -> None:
            self._subs.remove(cb)

        return unsub

    def set(self, value: str) -> None:
        self._value = value
        for cb in list(self._subs):
            cb()


def test_detects_interleaved_mutation_between_render_and_layout_effects() -> None:
    # Upstream: useSyncExternalStore-test.js
    # "detects interleaved mutations during a concurrent read before layout effects fire"
    #
    # Minimal noop-host slice: if the store mutates during insertion effects,
    # the hook should re-check the snapshot before layout effects and schedule
    # an update so the committed snapshot catches up on the next flush.
    root = create_noop_root()
    store = Store("A")

    def App() -> object:
        snap = use_sync_external_store(store.subscribe, store.get_snapshot)

        def mutate() -> None:
            store.set("B")

        use_insertion_effect(lambda: mutate() or None, ())
        return create_element("div", {"value": snap})

    root.render(create_element(App))
    committed = root.container.last_committed
    assert committed is not None
    assert committed["props"]["value"] == "A"

    root.flush()
    committed2 = root.container.last_committed
    assert committed2 is not None
    assert committed2["props"]["value"] == "B"
