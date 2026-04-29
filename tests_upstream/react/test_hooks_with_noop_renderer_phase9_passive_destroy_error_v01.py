from __future__ import annotations

from typing import Any

import pytest

from ryact import create_element, use_effect, use_state
from ryact_testkit import create_noop_root


def _span(value: str) -> Any:
    return create_element("span", {"text": value})


def test_handles_errors_in_destroy_on_update() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "handles errors in destroy on update"
    log: list[str] = []
    root = create_noop_root()
    set_tick: list[Any] = [None]

    def App() -> Any:
        tick, set_t = use_state(0)
        set_tick[0] = set_t

        def eff() -> Any:
            log.append(f"create:{tick}")

            def cleanup() -> None:
                log.append(f"cleanup:{tick}")
                if tick == 0:
                    raise RuntimeError("cleanup boom")

            return cleanup

        use_effect(eff, (tick,))
        return _span(str(tick))

    root.render(create_element(App))
    root.flush()
    assert log == ["create:0"]

    st = set_tick[0]
    assert callable(st)
    st(1)
    with pytest.raises(RuntimeError, match="cleanup boom"):
        root.flush()

    # Cleanup ran, and the new effect create should not have run after the error.
    assert log == ["create:0", "cleanup:0"]

