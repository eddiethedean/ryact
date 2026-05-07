from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress

from ryact import create_element, use_state, use_sync_external_store
from ryact_testkit import create_noop_root


def test_next_value_cached_when_render_phase_syncs_mirror_state() -> None:
    # Upstream: useSyncExternalStore-test.js
    # "next value is correctly cached when state is dispatched in render phase"
    store: dict[str, str] = {"v": "value:initial"}
    listeners: list[Callable[[], None]] = []

    def subscribe(cb: Callable[[], None]) -> Callable[[], None]:
        listeners.append(cb)

        def unsub() -> None:
            with suppress(ValueError):
                listeners.remove(cb)

        return unsub

    def get_snapshot() -> str:
        return store["v"]

    def App() -> object:
        value = use_sync_external_store(subscribe, get_snapshot)
        same, set_same = use_state(value)
        if value != same:
            set_same(value)
        return create_element("div", {"text": value})

    root = create_noop_root()
    root.render(create_element(App))
    root.flush()
    assert root.container.last_committed is not None
    assert root.container.last_committed["props"]["text"] == "value:initial"

    store["v"] = "value:changed"
    for cb in list(listeners):
        cb()
    root.flush()
    assert root.container.last_committed is not None
    assert root.container.last_committed["props"]["text"] == "value:changed"

    store["v"] = "value:initial"
    for cb in list(listeners):
        cb()
    root.flush()
    assert root.container.last_committed is not None
    assert root.container.last_committed["props"]["text"] == "value:initial"
