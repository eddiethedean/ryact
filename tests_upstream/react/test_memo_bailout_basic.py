from __future__ import annotations

from collections.abc import Callable

from ryact import create_element, memo, use_state
from ryact_testkit import create_noop_root


def test_bails_out_when_props_are_equal() -> None:
    # Upstream: ReactHooks-test.internal.js
    # "bails out in render phase if all the state is the same and props bail out with memo"
    root = create_noop_root()
    renders: list[str] = []
    set_tick: list[Callable[[int], None] | None] = [None]

    def Inner(*, label: str) -> object:
        renders.append(label)
        return create_element("div", {"label": label})

    MemoInner = memo(Inner)

    def App() -> object:
        tick, set_t = use_state(0)
        set_tick[0] = set_t
        # App re-renders, but MemoInner props stay equal.
        _ = tick
        return create_element(MemoInner, {"label": "A"})

    root.render(create_element(App))
    assert renders == ["A"]

    st = set_tick[0]
    assert st is not None
    st(1)
    root.flush()

    # Should not re-render Inner because memo props are equal.
    assert renders == ["A"]
