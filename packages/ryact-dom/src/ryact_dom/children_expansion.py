"""Host/component child expansion with ReactMultiChild DEV warnings."""

from __future__ import annotations

import inspect
import types
from collections.abc import Iterable, Iterator, Mapping
from typing import Any

from ryact.dev import is_dev
from ryact.element import Element

_ITERATOR_CHILDREN_MSG = (
    "Using Iterators as children is unsupported and will likely yield "
    "unexpected results because enumerating a generator mutates it. "
    "You may convert it to an array with `Array.from()` or the "
    "`[...spread]` operator before rendering. You can also use an "
    "Iterable that can iterate multiple times over the same items."
)
_MAP_CHILDREN_MSG = "Using Maps as children is not supported. Use an array of keyed ReactElements instead."

_warned_iterator_children: set[str] = set()
_warned_map_children: set[str] = set()


def reset_dom_children_warning_state() -> None:
    _warned_iterator_children.clear()
    _warned_map_children.clear()


def _warn_once(*, bucket: set[str], key: str, msg: str, owner_stack: str) -> None:
    if not is_dev() or key in bucket:
        return
    bucket.add(key)
    full = msg if not owner_stack else msg + "\n\n" + owner_stack
    import warnings

    warnings.warn(full, RuntimeWarning, stacklevel=5)


def _is_map_children(value: Any) -> bool:
    return type(value).__name__ == "Map" or bool(getattr(value, "_ryact_map_children", False))


def _is_bare_generator(value: Any) -> bool:
    return inspect.isgenerator(value) or isinstance(value, types.GeneratorType)


def _is_bare_iterator(value: Any) -> bool:
    if isinstance(value, (str, bytes, list, tuple, Element, dict)):
        return False
    if _is_map_children(value):
        return False
    if _is_bare_generator(value):
        return True
    return isinstance(value, Iterator) and hasattr(value, "__next__")


def _is_reusable_iterable_object(value: Any) -> bool:
    """Objects with ``__iter__`` on the container (not a bare generator iterator)."""

    if isinstance(value, (str, bytes, list, tuple, Element, dict)):
        return False
    if _is_map_children(value) or _is_bare_generator(value) or _is_bare_iterator(value):
        return False
    return hasattr(value, "__iter__") and not isinstance(value, Mapping)


def expand_rendered_children(value: Any, *, owner_stack: str = "") -> Any:
    """Normalize component return values; warn on bare generators/iterables."""

    if value is None or value is False or isinstance(value, (str, int, float, Element)):
        return value
    if isinstance(value, (list, tuple)) and not isinstance(value, (str, bytes, bytearray)) and len(value) == 1:
        inner = expand_rendered_children(value[0], owner_stack=owner_stack)
        if inner is not value[0]:
            return inner
    if _is_map_children(value):
        _warn_once(bucket=_warned_map_children, key="map", msg=_MAP_CHILDREN_MSG, owner_stack=owner_stack)
        return None
    if _is_bare_generator(value) or _is_bare_iterator(value):
        _warn_once(
            bucket=_warned_iterator_children,
            key="iterator",
            msg=_ITERATOR_CHILDREN_MSG,
            owner_stack=owner_stack,
        )
        from ryact.concurrent import Fragment
        from ryact.element import create_element

        return create_element(Fragment, {"children": tuple(value)})
    if _is_reusable_iterable_object(value):
        from ryact.concurrent import Fragment
        from ryact.element import create_element

        return create_element(Fragment, {"children": tuple(value)})
    return value


def _children_as_list(children: object) -> list[object]:
    if isinstance(children, (list, tuple)):
        return list(children)
    if isinstance(children, Iterable) and not isinstance(children, (str, bytes, Mapping)):
        return list(children)
    return [children]


def expand_host_children(children: object, *, owner_stack: str = "") -> list[object]:
    """Expand host ``children`` (skip null/false; flatten arrays; warn on Map/iterators)."""

    if children is None:
        return []
    if isinstance(children, (str, bytes)):
        return [children]
    if _is_map_children(children):
        _warn_once(bucket=_warned_map_children, key="map", msg=_MAP_CHILDREN_MSG, owner_stack=owner_stack)
        return []
    if _is_bare_generator(children) or _is_bare_iterator(children):
        _warn_once(
            bucket=_warned_iterator_children,
            key="iterator-host",
            msg=_ITERATOR_CHILDREN_MSG,
            owner_stack=owner_stack,
        )
        work = _children_as_list(children)
    elif (
        isinstance(children, (list, tuple))
        or _is_reusable_iterable_object(children)
        or (hasattr(children, "__iter__") and not isinstance(children, Mapping))
    ):
        work = _children_as_list(children)
    else:
        work = [children]
    out: list[object] = []
    for c in work:
        if c is None or c is False:
            continue
        if isinstance(c, (list, tuple)):
            out.extend(expand_host_children(c, owner_stack=owner_stack))
        elif _is_map_children(c):
            _warn_once(bucket=_warned_map_children, key="map", msg=_MAP_CHILDREN_MSG, owner_stack=owner_stack)
            continue
        elif _is_bare_generator(c) or _is_bare_iterator(c):
            _warn_once(
                bucket=_warned_iterator_children,
                key="iterator-host",
                msg=_ITERATOR_CHILDREN_MSG,
                owner_stack=owner_stack,
            )
            out.extend(expand_host_children(_children_as_list(c), owner_stack=owner_stack))
        elif _is_reusable_iterable_object(c):
            out.extend(expand_host_children(_children_as_list(c), owner_stack=owner_stack))
        else:
            out.append(c)
    return out
