from __future__ import annotations

from ryact import create_element
from ryact_dom import create_root
from ryact_dom.dom import Container, ElementNode, TextNode
from ryact.reconciler import LOW_LANE, SYNC_LANE
from schedulyr import NORMAL_PRIORITY, Scheduler


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


def test_flush_priority_upgrades_when_higher_priority_lane_arrives() -> None:
    sched = Scheduler()
    container = Container()
    root = create_root(container, scheduler=sched)

    root.render(create_element("div", {"id": "low"}, "low"), lane=LOW_LANE)

    observed_child_count: list[int] = []

    def observe_normal_priority() -> None:
        observed_child_count.append(len(container.root.children))

    sched.schedule_callback(NORMAL_PRIORITY, observe_normal_priority, delay_ms=0)

    # Upgrade: this should reschedule the coalesced flush at IMMEDIATE priority.
    root.render(create_element("div", {"id": "sync"}, "sync"), lane=SYNC_LANE)
    sched.run_until_idle()

    # The normal-priority observer should run after the upgraded flush.
    assert observed_child_count == [1]
    assert len(container.root.children) == 1
    div = container.root.children[0]
    assert isinstance(div, ElementNode)
    assert div.props["id"] == "sync"


def test_flush_priority_does_not_downgrade_when_lower_priority_lane_arrives() -> None:
    sched = Scheduler()
    container = Container()
    root = create_root(container, scheduler=sched)

    root.render(create_element("div", {"id": "sync"}, "sync"), lane=SYNC_LANE)

    observed_child_count: list[int] = []

    def observe_normal_priority() -> None:
        observed_child_count.append(len(container.root.children))

    sched.schedule_callback(NORMAL_PRIORITY, observe_normal_priority, delay_ms=0)

    # No downgrade: flush is already scheduled at IMMEDIATE, so this should not reschedule.
    root.render(create_element("div", {"id": "low"}, "low"), lane=LOW_LANE)
    sched.run_until_idle()

    assert observed_child_count == [1]
    assert len(container.root.children) == 1
    div = container.root.children[0]
    assert isinstance(div, ElementNode)
    # Coalescing still means "latest payload wins".
    assert div.props["id"] == "low"
