from __future__ import annotations

from collections.abc import Callable

from ryact import Component, create_element, use_state
from ryact.concurrent import Suspend, Thenable, suspense
from ryact_testkit import create_noop_root


class Inner(Component):
    """Class child inside a re-suspending tree (mirrors function-child slice)."""

    def render(self) -> object:
        step = int(self.props.get("step", 0))
        t0: Thenable = self.props["t0"]  # type: ignore[assignment]
        t1: Thenable = self.props["t1"]  # type: ignore[assignment]
        if step == 0:
            raise Suspend(t0)
        if step == 2:
            raise Suspend(t1)
        return create_element("span", {"text": f"step{step}"})


def test_class_child_suspend_resuspend_then_complete() -> None:
    # Upstream: ReactSuspenseEffectsSemantics-test.js
    # "should be destroyed and recreated for class components"
    t0, t1 = Thenable(), Thenable()
    api: dict[str, Callable[[int], None]] = {}

    def App() -> object:
        step, set_step = use_state(0)
        api["setStep"] = set_step
        return suspense(
            fallback=create_element("div", {"text": "fb"}),
            children=create_element(Inner, {"step": step, "t0": t0, "t1": t1}),
        )

    root = create_noop_root()
    root.render(create_element(App))
    assert root.container.last_committed == {
        "type": "div",
        "key": None,
        "props": {"text": "fb"},
        "children": [],
    }
    t0.resolve()
    api["setStep"](1)
    root.flush()
    assert root.container.last_committed == {
        "type": "span",
        "key": None,
        "props": {"text": "step1"},
        "children": [],
    }
    api["setStep"](2)
    root.flush()
    assert root.container.last_committed == {
        "type": "div",
        "key": None,
        "props": {"text": "fb"},
        "children": [],
    }
    t1.resolve()
    api["setStep"](3)
    root.flush()
    assert root.container.last_committed == {
        "type": "span",
        "key": None,
        "props": {"text": "step3"},
        "children": [],
    }
