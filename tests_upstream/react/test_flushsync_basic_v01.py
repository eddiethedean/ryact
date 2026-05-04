from __future__ import annotations

from typing import Any

from ryact import create_element
from ryact.hooks import use_effect, use_state
from ryact_testkit import create_noop_root


def _span(text: str) -> Any:
    return create_element("span", {"text": text})


def test_flushsync_runs_sync_updates_immediately_and_defers_passives() -> None:
    # Minimal acceptance slice: flush_sync flushes sync work now, but passive effects
    # are drained by a subsequent normal flush boundary.
    log: list[str] = []

    def App() -> Any:
        v, set_v = use_state("A")

        def eff() -> Any:
            log.append(f"effect:{v}")
            return None

        use_effect(eff, (v,))
        return _span(v)

    root = create_noop_root()
    root.render(create_element(App))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "A"
    assert log == ["effect:A"]
    log.clear()

    # Trigger a synchronous update inside a flushSync boundary.
    setter: list[object] = []

    def AppWithSetter() -> Any:
        v, set_v = use_state("A")
        if not setter:
            setter.append(set_v)

        def eff() -> Any:
            log.append(f"effect:{v}")
            return None

        use_effect(eff, (v,))
        return _span(v)

    root.render(create_element(AppWithSetter))
    root.flush()
    log.clear()

    set_v = setter[0]
    assert callable(set_v)
    root.flush_sync(lambda: set_v("B"))  # type: ignore[misc]
    # Effects are deferred during flush_sync (noop harness parity).
    assert log == []
    root.flush()
    assert "effect:B" in log

