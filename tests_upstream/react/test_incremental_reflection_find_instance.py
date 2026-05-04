from __future__ import annotations

from typing import Any

from ryact import Component, create_element
from ryact_testkit import create_noop_root
from schedulyr import Scheduler


def span(prop: Any | None = None) -> dict[str, Any]:
    return {"type": "span", "children": [], "prop": prop, "hidden": False}


def div(*children: Any) -> dict[str, Any]:
    norm = [{"text": c, "hidden": False} if isinstance(c, str) else c for c in children]
    return {"type": "div", "children": norm, "prop": None, "hidden": False}


def test_finds_no_node_before_insertion_and_correct_node_before_deletion() -> None:
    # Upstream: ReactIncrementalReflection-test.js
    log: list[Any] = []

    sched = Scheduler()
    root = create_noop_root(scheduler=sched)

    class_instance: Any | None = None

    def find_instance(inst: object) -> Any | None:
        return root.find_instance(inst)

    class ReflectionComponent(Component):
        def UNSAFE_componentWillMount(self) -> None:  # noqa: N802
            nonlocal class_instance
            class_instance = self
            log.append(["componentWillMount", find_instance(self)])

        def componentDidMount(self) -> None:  # noqa: N802
            log.append(["componentDidMount", find_instance(self)])

        def UNSAFE_componentWillUpdate(self) -> None:  # noqa: N802
            log.append(["componentWillUpdate", find_instance(self)])

        def componentDidUpdate(self) -> None:  # noqa: N802
            log.append(["componentDidUpdate", find_instance(self)])

        def componentWillUnmount(self) -> None:  # noqa: N802
            log.append(["componentWillUnmount", find_instance(self)])

        def render(self) -> Any:
            log.append("render")

            step = int(self.props["step"])

            def capture_span(n: Any) -> None:
                self.span = n  # type: ignore[attr-defined]

            def capture_div(n: Any) -> None:
                self.div = n  # type: ignore[attr-defined]

            if step < 2:
                return create_element("span", {"ref": capture_span})
            if step == 2:
                return create_element("div", {"ref": capture_div})
            if step == 3:
                return None
            if step == 4:
                return create_element("span", {"ref": capture_span})
            return None

    def Sibling(**_: Any) -> Any:
        log.append("render sibling")
        return create_element("div")

    def Foo(step: int) -> Any:
        return create_element(
            "div",
            {"key": "root"},
            create_element(ReflectionComponent, {"step": step, "key": "c"}),
            create_element(Sibling, {"key": "s"}),
        )

    # Initial mount is scheduled (not committed yet).
    root.render(create_element(Foo, {"step": 0}))
    assert class_instance is None

    # Nothing is committed yet so instance is not findable.
    sched.run_until_idle()
    assert class_instance is not None
    host_span = root.find_instance(class_instance)
    assert isinstance(host_span, dict) and host_span.get("type") == "span"

    # Update step 1 (still span).
    root.render(create_element(Foo, {"step": 1}))
    # Before flush, still old committed host span.
    assert root.find_instance(class_instance) is host_span
    sched.run_until_idle()
    assert root.find_instance(class_instance) is host_span

    # Update step 2 (div).
    root.render(create_element(Foo, {"step": 2}))
    assert root.find_instance(class_instance) is host_span
    sched.run_until_idle()
    host_div = root.find_instance(class_instance)
    assert isinstance(host_div, dict) and host_div.get("type") == "div"
    assert host_div is not host_span
    assert root.find_instance(class_instance) is host_div

    # Render to null.
    root.render(create_element(Foo, {"step": 3}))
    assert root.find_instance(class_instance) is host_div
    sched.run_until_idle()
    assert root.find_instance(class_instance) is None

    # Render a div again (step 4 produces span in upstream; we keep span semantics too).
    root.render(create_element(Foo, {"step": 4}))
    assert root.find_instance(class_instance) is None
    sched.run_until_idle()
    host_span2 = root.find_instance(class_instance)
    assert isinstance(host_span2, dict) and host_span2.get("type") == "span"

    # Unmount component
    root.render(None)
    sched.run_until_idle()

    # Sanity: lifecycle ordering captured at least once.
    assert ["componentWillMount", None] in log
