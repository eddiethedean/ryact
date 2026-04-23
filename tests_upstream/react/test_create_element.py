from __future__ import annotations

from ryact import create_element, h


def test_create_element_children_are_flattened_one_level() -> None:
    el = create_element("div", None, "a", ["b", "c"], ("d",))
    assert el.type == "div"
    assert el.props["children"] == ("a", "b", "c", "d")


def test_create_element_extracts_key_and_ref_from_props() -> None:
    el = create_element("div", {"key": "k1", "ref": object(), "id": "x"})
    assert el.key == "k1"
    assert el.ref is not None
    assert el.props["id"] == "x"


def test_create_element_merges_pythonic_kwargs() -> None:
    el = create_element("div", None, "a", id="x", tab_index=1)
    assert el.props["id"] == "x"
    assert el.props["tab_index"] == 1
    assert el.props["children"] == ("a",)


def test_create_element_kwargs_override_props_dict() -> None:
    el = create_element("div", {"id": "a"}, id="b")
    assert el.props["id"] == "b"


def test_create_element_children_kwarg_is_normalized() -> None:
    el = create_element("div", children=["a", ["b", "c"]])
    assert el.props["children"] == ("a", "b", "c")


def test_h_alias_matches_create_element() -> None:
    a = h("span", None, "x", title="t")
    b = create_element("span", None, "x", title="t")
    assert a.props == b.props


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
