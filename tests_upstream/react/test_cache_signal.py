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


def test_cache_signal_aborts_when_render_finishes_normally() -> None:
    # Upstream: ReactCache-test.js — "cacheSignal() aborts when the render finishes normally"
    seen: list[object] = []

    def App(**_: object) -> object:
        sig = cache_signal()
        assert sig is not None
        seen.append(sig)
        return create_element("div")

    root = create_noop_root()
    root.render(create_element(App))
    sig2 = seen[0]
    assert getattr(sig2, "aborted") is True


def test_cache_signal_aborts_when_render_is_aborted() -> None:
    # Upstream: ReactCache-test.js — "cacheSignal() aborts when the render is aborted"
    seen: list[object] = []

    def App(**_: object) -> object:
        sig = cache_signal()
        assert sig is not None
        seen.append(sig)
        raise RuntimeError("boom")

    root = create_noop_root()
    try:
        root.render(create_element(App))
    except RuntimeError:
        pass
    sig2 = seen[0]
    assert getattr(sig2, "aborted") is True


def test_cache_signal_aborts_when_render_suspends() -> None:
    # Upstream-adjacent: a suspended render attempt is an aborted attempt.
    from ryact.concurrent import Suspend, Thenable, suspense

    thenable = Thenable()
    seen: list[object] = []

    def Suspender(**_: object) -> object:
        sig = cache_signal()
        assert sig is not None
        seen.append(sig)
        raise Suspend(thenable)

    root = create_noop_root()
    root.render(suspense(fallback=create_element("div"), children=create_element(Suspender)))
    assert getattr(seen[0], "aborted") is True


def test_cache_signal_returns_unique_signals_per_call() -> None:
    seen: list[object] = []

    def App(**_: object) -> object:
        a = cache_signal()
        b = cache_signal()
        assert a is not None and b is not None
        seen.extend([a, b])
        return create_element("div")

    root = create_noop_root()
    root.render(create_element(App))
    assert len(seen) == 2
    assert seen[0] is not seen[1]

