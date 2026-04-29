from __future__ import annotations

from ryact import create_element, use_state
from ryact_testkit import create_noop_root


def test_bails_out_in_render_phase_if_all_state_is_the_same() -> None:
    # Upstream: ReactHooks-test.internal.js
    # "bails out in the render phase if all of the state is the same"
    root = create_noop_root()
    renders: list[int] = []
    did: dict[str, bool] = {"ran": False}

    def App() -> object:
        tick, set_t = use_state(0)
        renders.append(int(tick))
        if not did["ran"]:
            did["ran"] = True

            def same(prev: object) -> object:
                return prev

            # Render-phase state update that computes the same value.
            set_t(same)  # type: ignore[arg-type]
        return create_element("div", {"text": str(tick)})

    root.render(create_element(App))
    root.flush()
    assert renders == [0]

