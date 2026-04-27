from __future__ import annotations

from ryact.cache import cache


def test_cache_objects_and_primitive_arguments_and_a_mix_of_them() -> None:
    # Upstream: ReactCache-test.js
    # "cache objects and primitive arguments and a mix of them"
    calls: list[tuple[object, ...]] = []

    def combine(*args: object) -> tuple[object, ...]:
        calls.append(args)
        return args

    cached = cache(combine)

    obj1: dict[str, object] = {"x": 1}
    obj2: dict[str, object] = {"x": 1}

    assert cached("a", 1, obj1) == ("a", 1, obj1)
    assert cached("a", 1, obj1) == ("a", 1, obj1)
    assert cached("a", 1, obj2) == ("a", 1, obj2)
    assert cached("a", 2, obj1) == ("a", 2, obj1)
    assert cached("b", 1, obj1) == ("b", 1, obj1)

    # Same primitives + same object identity should hit the cache.
    # Different object identity or primitive value should miss.
    assert calls == [
        ("a", 1, obj1),
        ("a", 1, obj2),
        ("a", 2, obj1),
        ("b", 1, obj1),
    ]


def test_cached_functions_that_throw_should_cache_the_error() -> None:
    # Upstream: ReactCache-test.js
    # "cached functions that throw should cache the error"
    calls = 0

    def boom(x: int) -> int:
        nonlocal calls
        calls += 1
        raise RuntimeError(f"nope:{x}")

    cached = cache(boom)

    for _ in range(2):
        try:
            cached(1)
            assert False, "expected cached call to throw"
        except RuntimeError as err:
            assert "nope:1" in str(err)

    assert calls == 1


def test_introspection_of_returned_wrapper_function_is_same_on_client_and_server() -> None:
    # Upstream: ReactCache-test.js
    # "introspection of returned wrapper function is same on client and server"
    def add(a: int, b: int) -> int:
        "docstring"
        return a + b

    cached = cache(add)
    assert cached.__name__ == add.__name__
    assert cached.__doc__ == add.__doc__
    # wraps() should also preserve the underlying reference.
    assert getattr(cached, "__wrapped__", None) is add

