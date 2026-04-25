from __future__ import annotations

from ryact import create_element, use_deferred_value, use_state
from ryact_testkit import create_noop_root


def test_defers_during_initial_render_when_initial_value_is_provided() -> None:
    # Upstream: ReactDeferredValue-test.js
    # "defers during initial render when initialValue is provided, even if render is not sync"
    root = create_noop_root()

    def App() -> object:
        v, _ = use_state("A")
        dv = use_deferred_value(v, initial_value="(init)")
        return create_element("div", {"value": dv})

    root.render(create_element(App))
    committed = root.container.last_committed
    assert committed is not None
    assert committed["props"]["value"] == "(init)"

    root.flush()
    committed2 = root.container.last_committed
    assert committed2 is not None
    assert committed2["props"]["value"] == "A"
