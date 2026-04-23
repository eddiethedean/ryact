from __future__ import annotations

from ryact import create_element
from ryact_dom import create_root
from ryact_dom.dom import Container, ElementNode, TextNode
from schedulyr import Scheduler


def test_create_root_with_scheduler_defers_flush_until_run_until_idle() -> None:
    """Milestone 3: reconciler commits run via ``schedulyr`` when a scheduler is passed."""
    sched = Scheduler()
    container = Container()
    root = create_root(container, scheduler=sched)

    root.render(create_element("div", {"id": "x"}, "hi"))
    assert container.root.children == []

    sched.run_until_idle()
    assert len(container.root.children) == 1
    div = container.root.children[0]
    assert isinstance(div, ElementNode)
    assert div.tag == "div"
    assert div.props["id"] == "x"
    assert len(div.children) == 1
    assert isinstance(div.children[0], TextNode)
    assert div.children[0].text == "hi"


def test_two_renders_before_idle_coalesce_single_commit() -> None:
    sched = Scheduler()
    container = Container()
    root = create_root(container, scheduler=sched)

    root.render(create_element("div", {"id": "a"}, "first"))
    root.render(create_element("div", {"id": "b"}, "second"))
    sched.run_until_idle()

    assert len(container.root.children) == 1
    div = container.root.children[0]
    assert isinstance(div, ElementNode)
    assert div.props["id"] == "b"
    text = div.children[0]
    assert isinstance(text, TextNode)
    assert text.text == "second"
