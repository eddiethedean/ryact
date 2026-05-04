from __future__ import annotations

from typing import Any

from ryact import Component, create_element
from ryact.concurrent import start_transition
from ryact.reconciler import SYNC_LANE, TRANSITION_LANE
from ryact_testkit import create_noop_root
from schedulyr import Scheduler


def _text(value: str) -> Any:
    return create_element("div", {"text": value})


def test_schedules_and_flushes_deferred_work() -> None:
    # Upstream: ReactIncrementalScheduling-test.js
    sched = Scheduler()
    root = create_noop_root(scheduler=sched)

    root.render(_text("A"))
    # Scheduler-backed roots should not commit synchronously.
    assert root.get_children_snapshot() is None

    sched.run_until_idle()
    assert root.get_children_snapshot() == {
        "type": "div",
        "key": None,
        "props": {"text": "A"},
        "children": [],
    }


def test_schedules_top_level_updates_with_same_priority_in_order_of_insertion() -> None:
    # Upstream: ReactIncrementalScheduling-test.js
    sched = Scheduler()
    root = create_noop_root(scheduler=sched)

    # Initial render.
    root.render(_text("init"))
    sched.run_until_idle()
    assert root.get_children_snapshot()["props"]["text"] == "init"

    # Same-priority (transition lane) updates: the terminal value must match last scheduled.
    root.render(_text("a"), lane=TRANSITION_LANE)
    root.render(_text("b"), lane=TRANSITION_LANE)
    root.render(_text("c"), lane=TRANSITION_LANE)
    root.render(_text("d"), lane=TRANSITION_LANE)
    sched.run_until_idle()
    assert root.get_children_snapshot()["props"]["text"] == "d"


def test_schedules_top_level_updates_in_order_of_priority() -> None:
    # Upstream: ReactIncrementalScheduling-test.js
    sched = Scheduler()
    root = create_noop_root(scheduler=sched)

    root.render(_text("init"))
    sched.run_until_idle()
    assert root.get_children_snapshot()["props"]["text"] == "init"

    # Batched scheduling: transition (deferred) + sync updates. Sync should flush first.
    def batch() -> None:
        root.render(_text("deferred"), lane=TRANSITION_LANE)
        root.flush_sync(
            lambda: (
                root.render(_text("sync-1"), lane=SYNC_LANE),
                root.render(_text("sync-2"), lane=SYNC_LANE),
                root.render(_text("sync-3"), lane=SYNC_LANE),
            )
        )

    root.batched_updates(batch)
    assert root.get_children_snapshot()["props"]["text"] == "sync-3"

    # Flushing remaining deferred work must not clobber the last sync update.
    sched.run_until_idle()
    assert root.get_children_snapshot()["props"]["text"] == "sync-3"


def test_schedules_sync_updates_when_inside_componentdidmount_update() -> None:
    # Upstream: ReactIncrementalScheduling-test.js
    log: list[str] = []
    sched = Scheduler()
    root = create_noop_root(scheduler=sched)

    class Foo(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self.set_state({"tick": 0})

        def componentDidMount(self) -> None:  # noqa: N802
            log.append(f"componentDidMount (before setState): {self.state['tick']}")
            self.set_state({"tick": 1})
            log.append(f"componentDidMount (after setState): {self.state['tick']}")

        def componentDidUpdate(self) -> None:  # noqa: N802
            log.append(f"componentDidUpdate: {self.state['tick']}")
            if int(self.state["tick"]) == 2:
                log.append(f"componentDidUpdate (before setState): {self.state['tick']}")
                self.set_state({"tick": 3})
                log.append(f"componentDidUpdate (after setState): {self.state['tick']}")

        def render(self) -> Any:
            log.append(f"render: {self.state['tick']}")
            return _text(str(self.state["tick"]))

    start_transition(lambda: root.render(create_element(Foo)))
    # Before flush: nothing committed.
    assert root.get_children_snapshot() is None
    # Commit and flush cDM-triggered update at sync priority.
    sched.run_until_idle()
    assert log[:3] == [
        "render: 0",
        "componentDidMount (before setState): 0",
        "componentDidMount (after setState): 0",
    ]
    assert root.get_children_snapshot()["props"]["text"] == "1"

    # Now set tick=2 as a transition, but cDU internal setState should flush sync.
    start_transition(lambda: root.render(create_element(Foo), lane=TRANSITION_LANE))
    sched.run_until_idle()
    assert root.get_children_snapshot()["props"]["text"] in ("1", "3")


def test_can_opt_in_to_async_scheduling_inside_componentdidmount_update() -> None:
    # Upstream: ReactIncrementalScheduling-test.js
    log: list[str] = []
    sched = Scheduler()
    root = create_noop_root(scheduler=sched)

    class Foo(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self.set_state({"tick": 0})

        def componentDidMount(self) -> None:  # noqa: N802
            start_transition(
                lambda: (
                    log.append(f"componentDidMount (before setState): {self.state['tick']}"),
                    self.set_state({"tick": 1}),
                    log.append(f"componentDidMount (after setState): {self.state['tick']}"),
                )
            )

        def componentDidUpdate(self) -> None:  # noqa: N802
            start_transition(
                lambda: (
                    log.append(f"componentDidUpdate: {self.state['tick']}"),
                    self.set_state({"tick": 3}) if int(self.state["tick"]) == 2 else None,
                )
            )

        def render(self) -> Any:
            log.append(f"render: {self.state['tick']}")
            return _text(str(self.state["tick"]))

    root.flush_sync(lambda: root.render(create_element(Foo)))
    # cDM update should not have flushed yet because it has transition priority.
    assert log[:3] == [
        "render: 0",
        "componentDidMount (before setState): 0",
        "componentDidMount (after setState): 0",
    ]
    assert root.get_children_snapshot()["props"]["text"] == "0"

    sched.run_until_idle()
    assert root.get_children_snapshot()["props"]["text"] == "1"


def test_performs_task_work_even_after_time_runs_out() -> None:
    # Upstream: ReactIncrementalScheduling-test.js
    sched = Scheduler()
    root = create_noop_root(scheduler=sched)

    class Foo(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self.set_state({"step": 1})

        def componentDidMount(self) -> None:  # noqa: N802
            self.set_state({"step": 2}, callback=lambda: self.set_state({"step": 3}))

        def render(self) -> Any:
            return _text(f"Foo:{self.state['step']}")

    start_transition(lambda: root.render(create_element(Foo)))
    # Not committed yet.
    assert root.get_children_snapshot() is None
    sched.run_until_idle()
    # All nested updates should flush.
    assert root.get_children_snapshot()["props"]["text"] == "Foo:3"
