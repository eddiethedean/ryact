from __future__ import annotations

from collections.abc import Callable

from ryact import create_element, sync_external_store_server_reads, use_sync_external_store
from ryact_dom.server import render_to_string
from ryact_testkit import create_noop_root


def _subscribe_noop(_fn: Callable[[], None]) -> Callable[[], None]:
    return lambda: None


def test_server_snapshot_used_inside_server_reads_context() -> None:
    log: list[str] = []

    def get_snapshot() -> str:
        log.append("get_snapshot")
        return "client"

    def get_server_snapshot() -> str:
        log.append("get_server_snapshot")
        return "server"

    def App() -> object:
        text = use_sync_external_store(_subscribe_noop, get_snapshot, get_server_snapshot)
        return create_element("div", {"value": text})

    root = create_noop_root()
    with sync_external_store_server_reads():
        root.render(create_element(App))
        root.flush()

    assert log == ["get_server_snapshot"]
    c = root.container.last_committed
    assert c is not None
    assert c["props"]["value"] == "server"


def test_client_path_uses_get_snapshot_including_layout_recheck() -> None:
    log: list[str] = []

    def get_snapshot() -> str:
        log.append("get_snapshot")
        return "client"

    def get_server_snapshot() -> str:
        log.append("get_server_snapshot")
        return "server"

    def App() -> object:
        text = use_sync_external_store(_subscribe_noop, get_snapshot, get_server_snapshot)
        return create_element("div", {"value": text})

    root = create_noop_root()
    root.render(create_element(App))
    root.flush()

    assert "get_server_snapshot" not in log
    assert log.count("get_snapshot") >= 1
    c = root.container.last_committed
    assert c is not None
    assert c["props"]["value"] == "client"


def test_render_to_string_enables_server_snapshot_reads() -> None:
    log: list[str] = []

    def get_snapshot() -> str:
        log.append("get_snapshot")
        return "client"

    def get_server_snapshot() -> str:
        log.append("get_server_snapshot")
        return "server"

    def App() -> object:
        text = use_sync_external_store(_subscribe_noop, get_snapshot, get_server_snapshot)
        return create_element("span", {}, text)

    html = render_to_string(create_element(App))
    assert log == ["get_server_snapshot"]
    assert "server" in html
    assert "client" not in html
