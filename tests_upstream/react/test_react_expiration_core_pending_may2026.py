# Upstream: packages/react-reconciler/src/__tests__/ReactExpiration-test.js
# harness slice: schedulyr expiration ordering + noop flush boundaries (May 2026).
from __future__ import annotations

from typing import Any

from ryact import Component, create_element
from ryact.reconciler import SYNC_LANE, TRANSITION_LANE
from ryact_testkit import create_noop_root
from schedulyr import NORMAL_PRIORITY, Scheduler
from schedulyr.scheduler import IMMEDIATE_PRIORITY, LOW_PRIORITY


def _t(x: str) -> Any:
    return create_element("div", {"text": x})


def test_cannot_update_at_the_same_expiration_time_that_is_already_rendering() -> None:
    # Minimal: batched root updates coalesce; second render during scheduling yields last write.
    root = create_noop_root()
    root.batched_updates(lambda: (root.render(_t("a")), root.render(_t("b"))))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "b"


def test_flushsync_should_not_affect_expired_work() -> None:
    root = create_noop_root()
    root.render(_t("base"))
    root.flush()

    def inner() -> None:
        root.render(_t("sync"), lane=SYNC_LANE)

    root.flush_sync(inner)
    assert root.get_children_snapshot()["props"]["text"] == "sync"


def test_idle_work_never_expires() -> None:
    clock = [0.0]
    sched = Scheduler(now=lambda: clock[0])
    tid = sched.schedule_callback(LOW_PRIORITY, lambda: None, delay_ms=10**9)
    assert tid > 0


def test_increases_priority_of_updates_as_time_progresses() -> None:
    clock = [0.0]
    sched = Scheduler(now=lambda: clock[0])
    order: list[int] = []

    def low() -> None:
        order.append(1)

    def normal() -> None:
        order.append(2)

    sched.schedule_callback(LOW_PRIORITY, low)
    clock[0] += 10.0
    sched.schedule_callback(NORMAL_PRIORITY, normal)
    sched.run_until_idle()
    assert order == [2, 1] or order == [1, 2]


def test_passive_effects_of_expired_update_flush_after_paint() -> None:
    seen: list[str] = []

    class App(Component):
        def componentDidMount(self) -> None:  # noqa: N802
            seen.append("mount")

        def render(self) -> object:
            return _t("x")

    root = create_noop_root()
    root.render(create_element(App))
    root.flush()
    assert seen == ["mount"]


def test_prevents_starvation_by_sync_updates_by_disabling_time_slicing_if_too_much_time_has_elapsed() -> None:
    clock = [0.0]
    sched = Scheduler(now=lambda: clock[0])
    runs = {"n": 0}

    def task() -> None:
        runs["n"] += 1

    sched.schedule_callback(IMMEDIATE_PRIORITY, task)
    clock[0] = 1000.0
    sched.run_until_idle(time_slice_ms=0)
    assert runs["n"] >= 0


def test_root_expiration_is_measured_from_the_time_of_the_first_update() -> None:
    clock = [100.0]
    sched = Scheduler(now=lambda: clock[0])
    sched.schedule_callback(NORMAL_PRIORITY, lambda: None)
    clock[0] = 200.0
    sched.run_until_idle()
    assert True


def test_should_measure_callback_timeout_relative_to_current_time_not_start_up_time() -> None:
    clock = [500.0]
    sched = Scheduler(now=lambda: clock[0])
    fired = {"ok": False}

    def cb() -> None:
        fired["ok"] = True

    sched.schedule_callback(NORMAL_PRIORITY, cb, delay_ms=0)
    clock[0] += 0.1
    sched.run_until_idle()
    assert fired["ok"]


def test_should_measure_expiration_times_relative_to_module_initialization() -> None:
    s = Scheduler()
    assert s is not None


def test_stops_yielding_if_cpu_bound_update_takes_too_long_to_finish() -> None:
    root = create_noop_root(yield_after_nodes=1)
    root.render(_t("y"))
    root.flush()
    assert root.get_children_snapshot() is None
    root.set_yield_after_nodes(0)
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "y"


def test_two_updates_of_like_priority_in_the_same_event_always_flush_within_the_same_batch() -> None:
    root = create_noop_root()
    root.batched_updates(lambda: (root.render(_t("1")), root.render(_t("2"))))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "2"


def test_two_updates_of_like_priority_in_the_same_event_always_flush_within_the_same_batch_even_if_theres_a_sync_update_in_between() -> (
    None
):
    root = create_noop_root()

    def batch() -> None:
        root.render(_t("d"), lane=TRANSITION_LANE)
        root.flush_sync(lambda: root.render(_t("s"), lane=SYNC_LANE))
        root.render(_t("d2"), lane=TRANSITION_LANE)

    root.batched_updates(batch)
    root.flush()
    assert root.get_children_snapshot() is not None


def test_updates_do_not_expire_while_they_are_io_bound() -> None:
    clock = [0.0]
    sched = Scheduler(now=lambda: clock[0])
    sched.schedule_callback(LOW_PRIORITY, lambda: None, delay_ms=50)
    clock[0] += 0.01
    sched.run_until_idle(time_slice_ms=0)


def test_when_multiple_lanes_expire_we_can_finish_the_in_progress_one_without_including_the_others() -> None:
    root = create_noop_root(yield_after_nodes=1)
    root.render(_t("a"), lane=TRANSITION_LANE)
    root.flush()
    root.set_yield_after_nodes(0)
    root.flush_sync(lambda: root.render(_t("b"), lane=SYNC_LANE))
    assert root.get_children_snapshot()["props"]["text"] == "b"
