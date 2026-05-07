from __future__ import annotations

from collections.abc import Callable

from ryact import create_element, use_sync_external_store_with_selector
from ryact_dom.server import render_to_string
from ryact_testkit import create_noop_root


def _subscribe_noop(_fn: Callable[[], None]) -> Callable[[], None]:
    return lambda: None


def test_server_markup_reads_get_server_snapshot_not_get_snapshot() -> None:
    # Upstream: ReactDOMFizzServer-test.js
    # "calls getServerSnapshot instead of getSnapshot (with selector and isEqual)"
    client_reads: list[None] = []
    server_reads: list[None] = []

    def get_snapshot() -> dict[str, str]:
        client_reads.append(None)
        return {"env": "client", "other": "unrelated"}

    def get_server_snapshot() -> dict[str, str]:
        server_reads.append(None)
        return {"env": "server", "other": "unrelated"}

    def selector(st: dict[str, str]) -> dict[str, str]:
        return {"env": st["env"]}

    def is_equal(a: dict[str, str], b: dict[str, str]) -> bool:
        return a["env"] == b["env"]

    def App() -> object:
        sel = use_sync_external_store_with_selector(
            _subscribe_noop,
            get_snapshot,
            get_server_snapshot,
            selector,
            is_equal,
        )
        return create_element("span", {}, sel["env"])

    html = render_to_string(create_element(App))
    assert len(server_reads) == 1
    assert client_reads == []
    assert "server" in html


def test_client_noop_uses_get_snapshot_and_selector() -> None:
    client_reads: list[None] = []
    server_reads: list[None] = []

    def get_snapshot() -> dict[str, str]:
        client_reads.append(None)
        return {"env": "browser", "other": "x"}

    def get_server_snapshot() -> dict[str, str]:
        server_reads.append(None)
        return {"env": "server", "other": "x"}

    def selector(st: dict[str, str]) -> dict[str, str]:
        return {"env": st["env"]}

    def is_equal(a: dict[str, str], b: dict[str, str]) -> bool:
        return a["env"] == b["env"]

    def App() -> object:
        sel = use_sync_external_store_with_selector(
            _subscribe_noop,
            get_snapshot,
            get_server_snapshot,
            selector,
            is_equal,
        )
        return create_element("div", {"env": sel["env"]})

    root = create_noop_root()
    root.render(create_element(App))
    root.flush()
    assert len(client_reads) >= 1
    assert server_reads == []
    c = root.container.last_committed
    assert c is not None
    assert c["props"]["env"] == "browser"


def test_is_equal_avoids_update_when_only_unselected_slice_changes() -> None:
    store: dict[str, int] = {"n": 0, "noise": 0}
    listeners: list[Callable[[], None]] = []
    render_count: list[int] = [0]

    def subscribe(cb: Callable[[], None]) -> Callable[[], None]:
        listeners.append(cb)
        return lambda: None

    def get_snapshot() -> dict[str, int]:
        return {"n": store["n"], "noise": store["noise"]}

    def selector(st: dict[str, int]) -> dict[str, int]:
        return {"n": st["n"]}

    def is_equal(a: dict[str, int], b: dict[str, int]) -> bool:
        return a["n"] == b["n"]

    def App() -> object:
        render_count[0] += 1
        sel = use_sync_external_store_with_selector(
            subscribe,
            get_snapshot,
            None,
            selector,
            is_equal,
        )
        return create_element("div", {"n": sel["n"]})

    root = create_noop_root()
    root.render(create_element(App))
    root.flush()
    after_mount = render_count[0]

    store["noise"] = 99
    for cb in list(listeners):
        cb()
    root.flush()
    assert render_count[0] == after_mount

    store["n"] = 7
    for cb in list(listeners):
        cb()
    root.flush()
    assert render_count[0] == after_mount + 1
    c = root.container.last_committed
    assert c is not None
    assert c["props"]["n"] == 7
