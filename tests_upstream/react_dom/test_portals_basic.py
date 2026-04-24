from __future__ import annotations

from ryact import create_element, create_portal
from ryact_dom.dom import Container, ElementNode, TextNode
from ryact_dom.root import create_root


def test_portal_renders_children_into_target_container() -> None:
    a = Container()
    b = Container()
    root = create_root(a)

    root.render(
        create_element(
            "div",
            None,
            "host",
            create_portal(children=create_element("span", None, "in-portal"), container=b),
        )
    )

    assert [c.tag for c in a.root.children if hasattr(c, "tag")] == ["div"]
    div = a.root.children[0]
    assert isinstance(div, ElementNode)
    assert isinstance(div.children[0], TextNode)
    assert div.children[0].text == "host"

    assert [c.tag for c in b.root.children if hasattr(c, "tag")] == ["span"]
    span = b.root.children[0]
    assert isinstance(span, ElementNode)
    assert isinstance(span.children[0], TextNode)
    assert span.children[0].text == "in-portal"


def test_portal_unmount_clears_target_container() -> None:
    a = Container()
    b = Container()
    root = create_root(a)

    root.render(create_portal(children=create_element("span", None, "x"), container=b))
    assert len(b.root.children) == 1

    root.render(None)
    assert b.root.children == []
