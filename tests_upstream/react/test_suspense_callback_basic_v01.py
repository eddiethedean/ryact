from __future__ import annotations

from ryact.concurrent import Thenable, unstable_set_suspense_callback


def test_suspense_callback_is_called_on_thenable_resolution() -> None:
    seen: list[str] = []

    def cb(_t: Thenable, status: str) -> None:
        seen.append(status)

    unstable_set_suspense_callback(cb)
    try:
        t = Thenable()
        t.resolve(123)
        assert seen == ["fulfilled"]
    finally:
        unstable_set_suspense_callback(None)

