from __future__ import annotations

from typing import cast

from ryact import Component, create_element
from ryact.concurrent import fragment
from ryact_testkit import create_noop_root
from schedulyr import Scheduler


def test_applies_batched_updates_despite_errors_in_scheduling() -> None:
    # Upstream: ReactIncrementalErrorHandling-test.internal.js
    # "applies batched updates regardless despite errors in scheduling"
    api: dict[str, Component] = {}

    class A(Component):
        def render(self) -> object:
            api["a"] = self
            n = int(self.state.get("n", 0))
            return create_element("span", {"text": f"A{n}"})

    class B(Component):
        def render(self) -> object:
            api["b"] = self
            n = int(self.state.get("n", 0))
            return create_element("span", {"text": f"B{n}"})

    sched = Scheduler()
    root = create_noop_root(scheduler=sched)
    root.render(fragment(create_element(A, {"key": "a"}), create_element(B, {"key": "b"})))
    sched.run_until_idle()
    assert root.container.last_committed == [
        {"type": "span", "key": None, "props": {"text": "A0"}, "children": []},
        {"type": "span", "key": None, "props": {"text": "B0"}, "children": []},
    ]

    a = cast(A, api["a"])
    b = cast(B, api["b"])

    # Make scheduling throw *after* the update is enqueued.
    original = a._schedule_update  # type: ignore[attr-defined]
    assert original is not None

    def schedule_then_throw() -> None:
        original()
        raise RuntimeError("schedule boom")

    a._schedule_update = schedule_then_throw  # type: ignore[attr-defined]

    a.set_state({"n": 1})
    b.set_state({"n": 1})
    sched.run_until_idle()
    assert root.container.last_committed == [
        {"type": "span", "key": None, "props": {"text": "A1"}, "children": []},
        {"type": "span", "key": None, "props": {"text": "B1"}, "children": []},
    ]


def test_applies_nested_batched_updates_despite_errors_in_scheduling() -> None:
    # Upstream: ReactIncrementalErrorHandling-test.internal.js
    # "applies nested batched updates despite errors in scheduling"
    api: dict[str, Component] = {}

    class A(Component):
        def render(self) -> object:
            api["a"] = self
            n = int(self.state.get("n", 0))
            return create_element("span", {"text": f"A{n}"})

    class B(Component):
        def render(self) -> object:
            api["b"] = self
            n = int(self.state.get("n", 0))
            return create_element("span", {"text": f"B{n}"})

    sched = Scheduler()
    root = create_noop_root(scheduler=sched)
    root.render(fragment(create_element(A, {"key": "a"}), create_element(B, {"key": "b"})))
    sched.run_until_idle()

    a = cast(A, api["a"])
    b = cast(B, api["b"])

    # Nested scheduling: A's scheduling path triggers B's update before raising.
    original = a._schedule_update  # type: ignore[attr-defined]
    assert original is not None

    def nested_schedule_then_throw() -> None:
        original()
        b.set_state({"n": 1})
        raise RuntimeError("nested schedule boom")

    a._schedule_update = nested_schedule_then_throw  # type: ignore[attr-defined]

    a.set_state({"n": 1})
    sched.run_until_idle()
    assert root.container.last_committed == [
        {"type": "span", "key": None, "props": {"text": "A1"}, "children": []},
        {"type": "span", "key": None, "props": {"text": "B1"}, "children": []},
    ]


def test_can_unmount_error_boundary_before_it_is_handled() -> None:
    # Upstream: ReactIncrementalErrorHandling-test.internal.js
    # "can unmount an error boundary before it is handled"
    log: list[str] = []

    class Child(Component):
        def render(self) -> object:
            raise RuntimeError("boom")

    class Boundary(Component):
        @classmethod
        def getDerivedStateFromError(cls, _err: BaseException) -> dict[str, object] | None:  # noqa: N802
            return {"hasError": True}

        def componentDidCatch(self, _err: BaseException) -> None:  # noqa: N802
            log.append("componentDidCatch")

        def render(self) -> object:
            if bool(self.state.get("hasError")):
                return create_element("div", {"text": "fb"})
            return create_element(Child)

    sched = Scheduler()
    root = create_noop_root(scheduler=sched)

    # Defer work: schedule Boundary mount, then unmount before the scheduler flush runs.
    root.render(create_element(Boundary))
    root.render(None)
    sched.run_until_idle()

    assert log == []
    assert root.container.last_committed is None

