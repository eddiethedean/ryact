from __future__ import annotations

from ryact import create_element


def test_create_element_children_are_flattened_one_level() -> None:
    el = create_element("div", None, "a", ["b", "c"], ("d",))
    assert el.type == "div"
    assert el.props["children"] == ("a", "b", "c", "d")


def test_create_element_extracts_key_and_ref_from_props() -> None:
    el = create_element("div", {"key": "k1", "ref": object(), "id": "x"})
    assert el.key == "k1"
    assert el.ref is not None
    assert el.props["id"] == "x"


def test_scheduler_runs_delayed_work_deterministically() -> None:
    from ryact.scheduler import NORMAL_PRIORITY, Scheduler
    from ryact_testkit import FakeTimers

    timers = FakeTimers()
    sched = Scheduler(now=timers.now_seconds)
    seen = []

    sched.schedule_callback(NORMAL_PRIORITY, lambda: seen.append("a"), delay_ms=10)
    sched.run_until_idle()
    assert seen == []

    timers.advance(10)
    sched.run_until_idle()
    assert seen == ["a"]

