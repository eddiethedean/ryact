from __future__ import annotations

from collections.abc import Callable

from ryact import create_element, use_insertion_effect, use_layout_effect, use_state
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


def test_insertion_effects_run_after_snapshot_is_published_on_update() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "fires insertion effects after snapshots on update"
    root = create_noop_root()
    log: list[str] = []
    setter: list[Callable[[str], None] | None] = [None]

    def App() -> object:
        v, set_v = use_state("A")
        setter[0] = set_v

        def eff() -> None:
            committed = root.container.last_committed
            assert committed is not None
            log.append(committed["props"]["value"])

        use_insertion_effect(lambda: eff() or None, (v,))
        return create_element("div", {"value": v})

    root.render(create_element(App))
    assert log == ["A"]

    set_v = setter[0]
    assert set_v is not None
    set_v("B")
    root.flush()
    assert log == ["A", "B"]
