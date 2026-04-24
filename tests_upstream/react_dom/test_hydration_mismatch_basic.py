from __future__ import annotations

from ryact import create_element
from ryact_dom import hydrate_root
from ryact_dom.dom import Container, ElementNode, TextNode


def test_hydrate_root_reports_text_mismatch_recoverably() -> None:
    container = Container()
    # Pretend SSR output already exists.
    div = ElementNode(tag="div", props={"id": "x"})
    div.append_child(TextNode(text="server"))
    container.root.append_child(div)

    errors: list[str] = []

    def on_recoverable_error(err: Exception) -> None:
        errors.append(str(err))

    root = hydrate_root(
        container,
        create_element("div", {"id": "x"}, "client"),
        on_recoverable_error=on_recoverable_error,
    )

    # Hydration in this minimal slice replaces the tree and reports mismatch.
    assert errors and "mismatch" in errors[0].lower()
    assert root.container is container
    assert container.root.children and isinstance(container.root.children[0], ElementNode)
    assert container.root.children[0].children and isinstance(
        container.root.children[0].children[0], TextNode
    )
    assert container.root.children[0].children[0].text == "client"
