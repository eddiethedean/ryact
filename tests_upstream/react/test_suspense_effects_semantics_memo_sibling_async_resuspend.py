from __future__ import annotations

from typing import Callable, cast

from ryact import create_element, memo, use_state
from ryact.concurrent import Suspend, Thenable, suspense
from ryact_testkit import create_noop_root


def TextInner(**_kwargs: object) -> object:
    return create_element("span", {"text": "memo"})


MemoText = memo(TextInner, compare=lambda _a, _b: True)


def AsyncSide(**props: object) -> object:
    phase = int(props["phase"])  # type: ignore[arg-type]
    t0 = props["t0"]
    t1 = props["t1"]
    if phase == 0:
        raise Suspend(cast(Thenable, t0))
    if phase == 2:
        raise Suspend(cast(Thenable, t1))
    return create_element("span", {"text": f"p{phase}"})


def test_memoized_inner_survives_sibling_async_resuspend() -> None:
    # Upstream: ReactSuspenseEffectsSemantics-test.js
    # "should be destroyed and recreated even if there is a bailout because of memoization"
    t0, t1 = Thenable(), Thenable()
    api: dict[str, Callable[[int], None]] = {}

    def App() -> object:
        phase, set_phase = use_state(0)
        api["setPhase"] = set_phase
        return suspense(
            fallback=create_element("div", {"text": "fb"}),
            children=create_element(
                "div",
                None,
                create_element(MemoText, {"key": "memo"}),
                create_element(
                    AsyncSide,
                    {"key": "async", "phase": phase, "t0": t0, "t1": t1},
                ),
            ),
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
    cast(Callable[[int], None], api["setPhase"])(1)
    root.flush()
    snap = root.container.last_committed
    assert snap["type"] == "div"
    kids = snap["children"]
    assert len(kids) == 2
    assert kids[0]["props"]["text"] == "memo"
    assert kids[1]["props"]["text"] == "p1"

    cast(Callable[[int], None], api["setPhase"])(2)
    root.flush()
    assert root.container.last_committed["props"]["text"] == "fb"

    t1.resolve()
    cast(Callable[[int], None], api["setPhase"])(3)
    root.flush()
    snap2 = root.container.last_committed
    assert snap2["type"] == "div"
    k2 = snap2["children"]
    assert len(k2) == 2
    assert k2[0]["props"]["text"] == "memo"
    assert k2[1]["props"]["text"] == "p3"
