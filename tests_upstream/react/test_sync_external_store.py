from __future__ import annotations

from collections.abc import Callable

from ryact import create_element, use_sync_external_store
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


def test_does_not_infinite_loop_for_only_changing_store_reference_in_render() -> None:
    # Upstream: useSyncExternalStore-test.js
    # "regression: does not infinite loop for only changing store reference in render"
    root = create_noop_root()
    store = Store("A")

    def App() -> object:
        snap = use_sync_external_store(store.subscribe, store.get_snapshot)
        return create_element("div", {"value": snap})

    root.render(create_element(App))
    store.set("B")
    root.flush()
    committed = root.container.last_committed
    assert committed is not None
    assert committed["props"]["value"] == "B"
