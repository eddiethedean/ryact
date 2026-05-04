from __future__ import annotations

from typing import Any, Callable

from ryact import create_element
from ryact.hooks import use_sync_external_store
from ryact_testkit import create_noop_root


def _div(text: str) -> Any:
    return create_element("div", {"text": text})


def test_use_sync_external_store_subscribe_updates_snapshot() -> None:
    value = {"v": 0}
    listeners: list[Callable[[], None]] = []

    def subscribe(fn: Callable[[], None]) -> Callable[[], None]:
        listeners.append(fn)

        def unsub() -> None:
            with contextlib.suppress(ValueError):
                listeners.remove(fn)

        return unsub

    def get_snapshot() -> int:
        return int(value["v"])

    def App() -> Any:
        snap = use_sync_external_store(subscribe, get_snapshot)
        return _div(str(snap))

    import contextlib

    root = create_noop_root()
    root.render(create_element(App))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "0"

    value["v"] = 1
    for fn in list(listeners):
        fn()
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "1"

