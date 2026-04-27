from __future__ import annotations

from typing import Callable, cast

from ryact import create_element, use_state
from ryact.concurrent import Suspend, Thenable, suspense
from ryact_testkit import create_noop_root


def Inner(*, step: int, t0: Thenable, t1: Thenable) -> object:
    # Upstream: function child inside a re-suspending tree.
    if step == 0:
        raise Suspend(t0)
    if step == 2:
        raise Suspend(t1)
    return create_element("span", {"text": f"step{step}"})


def test_function_child_suspend_resuspend_then_complete() -> None:
    # Upstream: ReactSuspenseEffectsSemantics-test.js
    # "should be destroyed and recreated for function components"
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
    cast(Callable[[int], None], api["setStep"])(1)
    root.flush()
    assert root.container.last_committed == {
        "type": "span",
        "key": None,
        "props": {"text": "step1"},
        "children": [],
    }
    cast(Callable[[int], None], api["setStep"])(2)
    root.flush()
    assert root.container.last_committed == {
        "type": "div",
        "key": None,
        "props": {"text": "fb"},
        "children": [],
    }
    t1.resolve()
    cast(Callable[[int], None], api["setStep"])(3)
    root.flush()
    assert root.container.last_committed == {
        "type": "span",
        "key": None,
        "props": {"text": "step3"},
        "children": [],
    }
