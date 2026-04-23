from __future__ import annotations

from ryact import create_element
from ryact_dom import create_root, render_to_string
from ryact_dom.dom import Container, ElementNode, TextNode


def test_create_root_renders_simple_tree() -> None:
    container = Container()
    root = create_root(container)
    root.render(create_element("div", {"id": "a"}, "hello"))

    assert len(container.root.children) == 1
    div = container.root.children[0]
    assert isinstance(div, ElementNode)
    assert div.tag == "div"
    assert div.props["id"] == "a"
    assert len(div.children) == 1
    text = div.children[0]
    assert isinstance(text, TextNode)
    assert text.text == "hello"


def test_function_component_renders() -> None:
    def Hello(name: str) -> object:
        return create_element("span", None, f"hi {name}")

    container = Container()
    root = create_root(container)
    root.render(create_element(Hello, {"name": "sam"}))

    span = container.root.children[0]
    assert isinstance(span, ElementNode)
    assert span.tag == "span"
    assert span.children[0].text == "hi sam"  # type: ignore[attr-defined]


def test_use_state_persists_between_renders() -> None:
    from ryact import use_state

    def Counter() -> object:
        count, set_count = use_state(0)
        # mutate state to verify persistence; the second render should observe the new value
        if count == 0:
            set_count(1)
        return create_element("div", None, str(count))

    container = Container()
    root = create_root(container)
    root.render(create_element(Counter, None))
    div = container.root.children[0]
    assert div.children[0].text == "0"  # type: ignore[attr-defined]

    root.render(create_element(Counter, None))
    div2 = container.root.children[0]
    assert div2.children[0].text == "1"  # type: ignore[attr-defined]


def test_dom_event_bubbles_to_parent_listener() -> None:
    seen = []

    def on_parent_click(event) -> None:
        seen.append(("parent", event.type, event.current_target.tag))

    def on_child_click(event) -> None:
        seen.append(("child", event.type, event.current_target.tag))

    container = Container()
    root = create_root(container)
    root.render(
        create_element(
            "div",
            {"onClick": on_parent_click},
            create_element("button", {"onClick": on_child_click}, "ok"),
        )
    )

    div = container.root.children[0]
    button = div.children[0]
    button.dispatch_event("click")  # type: ignore[attr-defined]

    assert seen[0][0] == "child"
    assert seen[1][0] == "parent"


def test_server_render_to_string_smoke() -> None:
    html = render_to_string(create_element("div", {"id": "x"}, "hi"))
    assert html == '<div id="x">hi</div>'

