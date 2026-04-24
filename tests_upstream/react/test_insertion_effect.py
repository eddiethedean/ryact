from __future__ import annotations

from ryact import create_element, use_insertion_effect, use_layout_effect
from ryact_testkit import create_noop_root


def test_insertion_effects_run_before_layout_effects() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "fires all insertion effects (interleaved) before firing any layout effects"
    root = create_noop_root()
    log: list[str] = []

    def App() -> object:
        use_insertion_effect(lambda: log.append("insertion") or None, ())
        use_layout_effect(lambda: log.append("layout") or None, ())
        return create_element("div")

    root.render(create_element(App))
    assert log == ["insertion", "layout"]
