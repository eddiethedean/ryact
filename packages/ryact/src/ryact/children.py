from __future__ import annotations

import re
import warnings
from collections.abc import Callable, Iterable
from dataclasses import replace
from typing import Any

from .concurrent import Fragment, Portal
from .dev import is_dev
from .element import Element


def _is_iterable_child(x: Any) -> bool:
    if isinstance(x, (str, bytes)):
        return False
    # Dicts are treated as opaque objects (React throws for objects in some cases).
    if isinstance(x, dict):
        return False
    # React #4776: never treat numbers/bools as iterable children, even if a host or test
    # monkey-patches ``__iter__`` onto int subclasses (JS ``Number.prototype[@@iterator]``).
    if isinstance(x, bool):
        return False
    if isinstance(x, (int, float)):
        return False
    try:
        iter(x)
        return isinstance(x, Iterable)
    except Exception:
        return False


def _flatten_children(children: Any, *, keep_none: bool) -> list[Any]:
    """
    Flatten nested child structures into a list, similar to React.Children traversal.

    Notes:
    - We treat tuples/lists/iterables as child collections.
    - We keep `None` values (ReactChildren-test asserts count/toArray semantics around
      null/undefined).
    """
    if children is None:
        return [None] if keep_none else []
    # Elements are leaf children (even if they contain their own props.children).
    if isinstance(children, Element):
        # React.Children traverses into Fragments.
        if children.type == Fragment:
            nested = children.props.get("children", ())
            outf: list[Any] = []
            for c in nested:
                outf.extend(_flatten_children(c, keep_none=True))
            return outf
        return [children]
    if isinstance(children, (list, tuple)):
        out: list[Any] = []
        for c in children:
            out.extend(_flatten_children(c, keep_none=True))
        return out
    if _is_iterable_child(children):
        out2: list[Any] = []
        for c in children:
            out2.extend(_flatten_children(c, keep_none=True))
        return out2
    return [children]


def _escape_key(key: str) -> str:
    # Minimal escape (React does more; expanded by tests).
    return key.replace("/", "//")


def _child_key(child: Any, index: int) -> str:
    if isinstance(child, Element) and child.key is not None:
        return _escape_key(str(child.key))
    return str(index)


def children_count(children: Any) -> int:
    return len(_flatten_children(children, keep_none=False))


def children_for_each(children: Any, fn: Callable[..., Any], ctx: Any | None = None) -> None:
    flat = _flatten_children(children, keep_none=False)
    for i, c in enumerate(flat):
        if ctx is None:
            fn(c, i)
        else:
            fn(ctx, c, i)


def children_map(children: Any, fn: Callable[..., Any], ctx: Any | None = None) -> list[Any]:
    flat = _flatten_children(children, keep_none=False)
    out: list[Any] = []
    for i, c in enumerate(flat):
        mapped = fn(c, i) if ctx is None else fn(ctx, c, i)

        if mapped is None:
            out.append(None)
            continue

        # If mapping returns an array/iterable, React combines keys; we approximate by
        # preserving returned element keys and prefixing with the original key.
        if isinstance(mapped, (list, tuple)) or _is_iterable_child(mapped):
            prefix = _child_key(c, i)
            for j, m in enumerate(_flatten_children(mapped, keep_none=True)):
                if isinstance(m, Element):
                    k = m.key if m.key is not None else str(j)
                    out.append(replace(m, key=f"{prefix}:{k}"))
                else:
                    out.append(m)
            continue

        if isinstance(mapped, Element) and isinstance(c, Element) and c.key is not None:
            # Retain key across mappings (minimal).
            out.append(replace(mapped, key=str(c.key)))
        else:
            out.append(mapped)
    return out


def children_to_array(children: Any) -> list[Any]:
    """
    Flatten children to an array and ensure Elements have stable keys.
    """
    flat = _flatten_children(children, keep_none=False)
    out: list[Any] = []
    for i, c in enumerate(flat):
        if isinstance(c, Element):
            key = c.key if c.key is not None else _child_key(c, i)
            out.append(replace(c, key=str(key)))
        else:
            out.append(c)
    return out


def only_child(children: Any) -> Any:
    flat = _flatten_children(children, keep_none=False)
    if len(flat) != 1:
        raise ValueError("Expected exactly one child.")
    c = flat[0]
    # ReactChildren-test has explicit throws for certain object types.
    if isinstance(c, (dict, re.Pattern)):
        raise TypeError("Invalid child type.")
    return c


def warn_if_missing_keys(
    children: Any,
    *,
    stacklevel: int = 2,
    parent_display_name: str | None = None,
) -> None:
    """
    DEV-only warning helper for missing keys in list children.
    """
    if not is_dev():
        return
    flat = _flatten_children(children, keep_none=False)
    element_children = [c for c in flat if isinstance(c, Element)]
    if len(element_children) < 2:
        return
    if any(c.key is None for c in element_children):
        msg = 'Each child in a list should have a unique "key" prop.'
        if parent_display_name:
            from ryact.devtools import format_component_stack

            msg = msg + "\n\n" + format_component_stack([parent_display_name])
        warnings.warn(
            msg,
            RuntimeWarning,
            stacklevel=stacklevel,
        )


class Children:
    count = staticmethod(children_count)
    for_each = staticmethod(children_for_each)
    map = staticmethod(children_map)
    to_array = staticmethod(children_to_array)
    only = staticmethod(only_child)


def _is_portal_element(node: Any) -> bool:
    return isinstance(node, Element) and node.type == Portal


def _is_fragment_element(node: Any) -> bool:
    return isinstance(node, Element) and node.type == Fragment
