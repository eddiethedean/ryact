from __future__ import annotations

import pytest

from ryact import cache


def test_cache_objects_and_primitive_arguments_and_a_mix_of_them() -> None:
    # Upstream: ReactCache-test.js — "cache objects and primitive arguments and a mix of them"
    calls: list[tuple[object, ...]] = []

    def add(a: object, b: object) -> tuple[object, object]:
        calls.append((a, b))
        return (a, b)

    cached = cache(add)

    o1 = object()
    o2 = object()
    assert cached(1, 2) == (1, 2)
    assert cached(1, 2) == (1, 2)
    assert cached(o1, 2) == (o1, 2)
    assert cached(o1, 2) == (o1, 2)
    assert cached(o2, 2) == (o2, 2)

    # Only first occurrences per key should call through.
    assert calls == [(1, 2), (o1, 2), (o2, 2)]


def test_cached_functions_that_throw_should_cache_the_error() -> None:
    # Upstream: ReactCache-test.js — "cached functions that throw should cache the error"
    calls: list[str] = []

    def boom(x: int) -> int:
        calls.append("call")
        raise RuntimeError(f"boom:{x}")

    cached = cache(boom)
    with pytest.raises(RuntimeError, match="boom:1") as e1:
        cached(1)
    with pytest.raises(RuntimeError, match="boom:1") as e2:
        cached(1)

    # Should be same cached exception instance.
    assert e1.value is e2.value
    assert calls == ["call"]


def test_introspection_of_returned_wrapper_function_is_same() -> None:
    # Upstream: ReactCache-test.js — "introspection of returned wrapper function is same on client and server"
    def fn(a: int, b: int) -> int:
        return a + b

    cached = cache(fn)
    assert cached.__name__ == fn.__name__
    assert cached.__doc__ == fn.__doc__

