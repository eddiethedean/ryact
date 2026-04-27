from __future__ import annotations

from ryact import cache_signal, create_element
from ryact_testkit import create_noop_root


def test_cache_signal_returns_none_outside_a_render() -> None:
    # Upstream: ReactCache-test.js — "cacheSignal() returns null outside a render"
    assert cache_signal() is None


def test_cache_signal_returns_value_inside_render() -> None:
    def App(**_: object) -> object:
        sig = cache_signal()
        assert sig is not None
        assert sig.aborted is False
        return create_element("div")

    root = create_noop_root()
    root.render(create_element(App))

