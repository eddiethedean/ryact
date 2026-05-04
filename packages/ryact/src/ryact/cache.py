from __future__ import annotations

import contextlib
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from typing import TypeVar, cast

T = TypeVar("T")


@dataclass
class CacheSignal:
    aborted: bool = False


def cache_signal() -> CacheSignal | None:
    # Upstream: ReactCache cacheSignal() returns null outside a render.
    # We model "inside a render" as having an active hook frame.
    from .hooks import _current_frame

    if _current_frame is None:
        return None
    sig = CacheSignal(aborted=False)
    with contextlib.suppress(Exception):
        getattr(_current_frame, "cache_signals", []).append(sig)
    return sig


def cache(fn: Callable[..., T]) -> Callable[..., T]:
    """
    Minimal ReactCache-like `cache()` wrapper.

    - Memoizes return values keyed by argument identity/value.
    - Caches raised exceptions as well (rethrows same error instance).
    """

    store: dict[tuple[object, ...], object] = {}

    def key_for(args: tuple[object, ...], kwargs: dict[str, object]) -> tuple[object, ...]:
        # We approximate React's cache keying: primitives by value, objects by identity.
        key_parts: list[object] = []
        for a in args:
            if isinstance(a, (str, int, float, bool, type(None))):
                key_parts.append(("v", a))
            else:
                key_parts.append(("id", id(a)))
        if kwargs:
            for k in sorted(kwargs.keys()):
                v = kwargs[k]
                if isinstance(v, (str, int, float, bool, type(None))):
                    key_parts.append(("kwv", k, v))
                else:
                    key_parts.append(("kwid", k, id(v)))
        return tuple(key_parts)

    @wraps(fn)
    def wrapped(*args: object, **kwargs: object) -> T:
        k = key_for(args, kwargs)
        if k in store:
            value = store[k]
            if isinstance(value, BaseException):
                raise value
            return cast(T, value)
        try:
            value = fn(*args, **kwargs)
        except BaseException as err:
            store[k] = err
            raise
        store[k] = value
        return value

    return wrapped


def get_cache_for_type(factory: Callable[[], T]) -> T:
    """
    Minimal `unstable_getCacheForType`-like helper.

    Returns a memoized value for `factory` identity for the duration of a single render
    attempt (i.e. while a hook frame is active).
    """
    from .hooks import _current_frame

    frame = _current_frame
    if frame is None:
        # Upstream returns a cache, but outside render this API is not meaningful.
        return factory()
    cache_by_type = getattr(frame, "_cache_for_type", None)
    if not isinstance(cache_by_type, dict):
        cache_by_type = {}
        frame._cache_for_type = cache_by_type
    key = factory
    if key in cache_by_type:
        return cast(T, cache_by_type[key])
    v = factory()
    cache_by_type[key] = v
    return v


# React parity aliases (naming)
def unstable_get_cache_for_type(factory: Callable[[], T]) -> T:
    return get_cache_for_type(factory)


def unstable_getCacheForType(factory: Callable[[], T]) -> T:  # noqa: N802
    return get_cache_for_type(factory)
