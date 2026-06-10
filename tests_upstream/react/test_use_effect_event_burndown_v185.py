# Translated from: packages/react-reconciler/src/__tests__/useEffectEvent-test.js
# Burndown v185: useEffectEvent doc integration examples (chat room + logVisit).
from __future__ import annotations

from typing import Any

from ryact import (
    PureComponent,
    create_element,
    create_ref,
    use_context,
    use_effect,
    use_effect_event,
    use_memo,
    use_state,
)
from ryact.context import context_provider, create_context
from ryact_testkit import FakeTimers, act, create_noop_root, set_act_environment_enabled


def _text(log: list[str], label: str) -> Any:
    log.append(label)
    return create_element("span", {"text": label})


def _texts_in_snapshot(node: Any) -> list[str]:
    if node is None:
        return []
    if isinstance(node, str):
        return [node]
    if isinstance(node, dict):
        out: list[str] = []
        props = node.get("props") or {}
        if "text" in props:
            out.append(str(props["text"]))
        for ch in props.get("children") or []:
            out.extend(_texts_in_snapshot(ch))
        return out
    if isinstance(node, list):
        merged: list[str] = []
        for item in node:
            merged.extend(_texts_in_snapshot(item))
        return merged
    return []


def _assert_snapshot_texts(root: Any, expected: list[str]) -> None:
    snap = root.get_children_snapshot()
    assert _texts_in_snapshot(snap) == expected


def _create_connection(*, timers: FakeTimers) -> dict[str, Any]:
    connected_callback: Any = None
    timeout_id: int | None = None

    def connect() -> None:
        nonlocal timeout_id

        def fire() -> None:
            if connected_callback is not None:
                connected_callback()

        timeout_id = timers.set_timeout(fire, 100)

    def on(event: str, callback: Any) -> None:
        nonlocal connected_callback
        if connected_callback is not None:
            raise RuntimeError("Cannot add the handler twice.")
        if event != "connected":
            raise RuntimeError('Only "connected" event is supported.')
        connected_callback = callback

    def disconnect() -> None:
        nonlocal timeout_id
        timeout_id = None

    return {"connect": connect, "on": on, "disconnect": disconnect}


def test_integration_implements_docs_chat_room_example() -> None:
    log: list[str] = []
    timers = FakeTimers()

    def ChatRoom(props: dict[str, Any]) -> object:
        room_id = str(props["roomId"])
        theme = str(props["theme"])
        on_connected = use_effect_event(lambda: log.append(f"Connected! theme: {theme}"))

        def effect() -> Any:
            connection = _create_connection(timers=timers)

            def on_event(event: str, callback: Any) -> None:
                connection["on"](event, callback)

            on_event("connected", lambda: on_connected())
            connection["connect"]()
            return connection["disconnect"]

        use_effect(effect, (room_id,))
        return _text(log, f"Welcome to the {room_id} room!")

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(ChatRoom, {"roomId": "general", "theme": "light"}))
        timers.advance(100)
        root.flush()
        assert log == ["Welcome to the general room!", "Connected! theme: light"]
        _assert_snapshot_texts(root, ["Welcome to the general room!"])

        log.clear()
        with act(flush=root.flush):
            root.render(create_element(ChatRoom, {"roomId": "music", "theme": "light"}))
        timers.advance(100)
        root.flush()
        assert log == ["Welcome to the music room!", "Connected! theme: light"]
        _assert_snapshot_texts(root, ["Welcome to the music room!"])

        log.clear()
        with act(flush=root.flush):
            root.render(create_element(ChatRoom, {"roomId": "music", "theme": "dark"}))
        assert log == ["Welcome to the music room!"]
        _assert_snapshot_texts(root, ["Welcome to the music room!"])

        log.clear()
        with act(flush=root.flush):
            root.render(create_element(ChatRoom, {"roomId": "travel", "theme": "dark"}))
        timers.advance(100)
        root.flush()
        assert log == ["Welcome to the travel room!", "Connected! theme: dark"]
        _assert_snapshot_texts(root, ["Welcome to the travel room!"])
    finally:
        set_act_environment_enabled(False)


def test_integration_implements_the_docs_logvisit_example() -> None:
    log: list[str] = []
    button = create_ref()

    class AddToCartButton(PureComponent):
        def add_to_cart(self) -> None:
            on_click = self.props.get("onClick")
            if callable(on_click):
                on_click()

        def render(self) -> object:
            return _text(log, "Add to cart")

    shopping_cart_context = create_context(None)

    def AppShell(*, children: Any) -> object:
        items, update_items = use_state(list[int])
        value = use_memo(lambda: {"items": items, "updateItems": update_items}, (items, update_items))
        return context_provider(shopping_cart_context, value, children)

    def Page(props: dict[str, Any]) -> object:
        url = str(props["url"])
        cart = use_context(shopping_cart_context)
        assert isinstance(cart, dict)
        items = cart["items"]
        update_items = cart["updateItems"]
        on_click = use_effect_event(lambda: update_items([*items, 1]))
        number_of_items = len(items)

        on_visit = use_effect_event(
            lambda visited_url: log.append(f"url: {visited_url}, numberOfItems: {number_of_items}")
        )

        use_effect(lambda: on_visit(url), (url,))
        return create_element(AddToCartButton, {"onClick": on_click, "ref": button})

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(
                create_element(AppShell, {"children": create_element(Page, {"url": "/shop/1"})})
            )
        root.flush()
        assert log == ["Add to cart", "url: /shop/1, numberOfItems: 0"]

        log.clear()
        with act(flush=root.flush):
            inst = button.current
            assert inst is not None
            inst.add_to_cart()
        root.flush()
        assert log == ["Add to cart"]

        log.clear()
        with act(flush=root.flush):
            root.render(
                create_element(AppShell, {"children": create_element(Page, {"url": "/shop/2"})})
            )
        root.flush()
        assert log == ["Add to cart", "url: /shop/2, numberOfItems: 1"]
    finally:
        set_act_environment_enabled(False)
