from __future__ import annotations

from collections.abc import Callable

from ryact import create_element, use_insertion_effect, use_state
from ryact_testkit import WarningCapture, create_noop_root


def test_warns_when_setstate_is_called_from_insertion_effect_setup() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "warns when setState is called from insertion effect setup"
    root = create_noop_root()
    setter: list[Callable[[int], None] | None] = [None]

    def App() -> object:
        n, set_n = use_state(0)
        setter[0] = set_n

        def eff() -> Callable[[], None] | None:
            set_n(n + 1)
            return None

        use_insertion_effect(eff, (n,))
        return create_element("div", {"value": n})

    with WarningCapture() as wc:
        root.render(create_element(App))
        # Flush any scheduled update triggered during commit.
        root.flush()

    wc.assert_any("Cannot update state from within an insertion effect")
