from __future__ import annotations

from collections.abc import Callable

from ryact import create_element, forward_ref, memo, use_state
from ryact_testkit import create_noop_root


def test_bails_out_if_forward_ref_is_wrapped_in_memo() -> None:
    # Upstream: forwardRef-test.js
    # "should bailout if forwardRef is wrapped in memo"
    root = create_noop_root()
    renders: list[str] = []
    set_tick: list[Callable[[int], None] | None] = [None]

    def render(props: dict[str, object], ref: object | None) -> object:
        _ = ref
        renders.append(str(props.get("label")))
        return create_element("div", {"label": props.get("label")})

    F = forward_ref(render)
    MF = memo(F)

    def App() -> object:
        tick, set_t = use_state(0)
        set_tick[0] = set_t
        _ = tick
        return create_element(MF, {"label": "A"})

    root.render(create_element(App))
    assert renders == ["A"]

    st = set_tick[0]
    assert st is not None
    st(1)
    root.flush()
    assert renders == ["A"]
