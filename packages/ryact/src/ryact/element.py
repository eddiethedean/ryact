from __future__ import annotations

import warnings
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, fields, is_dataclass
from typing import Any, Generic, TypeVar, Union

from .dev import is_dev

TType = TypeVar("TType")
TProps = TypeVar("TProps", bound=Mapping[str, Any])


@dataclass(frozen=True)
class Element(Generic[TType, TProps]):
    type: TType
    props: TProps
    key: str | None = None
    ref: Any | None = None


ChildrenInput = Union[Sequence[Any], Any, None]

_FRAGMENT = "__fragment__"


def _maybe_warn_host_children_keys(type_: Any, children: tuple[Any, ...]) -> None:
    if not isinstance(type_, str) or not is_dev() or len(children) < 2:
        return
    from .children import warn_if_missing_keys

    warn_if_missing_keys(children, stacklevel=3, parent_display_name=str(type_))


def _warn_if_illegal_fragment_props(type_: Any, props_dict: dict[str, Any]) -> None:
    if type_ != _FRAGMENT or not is_dev():
        return
    illegal = [k for k in props_dict if k != "children"]
    if not illegal:
        return
    warnings.warn(
        "Invalid prop(s) supplied to React.Fragment. "
        f"Only the children prop is supported; received: {', '.join(sorted(illegal))}.",
        UserWarning,
        stacklevel=2,
    )


def _normalize_children(children: ChildrenInput) -> tuple[Any, ...]:
    if children is None:
        return ()
    if isinstance(children, (list, tuple)):
        out = []  # type: list[Any]
        for c in children:
            if isinstance(c, (list, tuple)):
                out.extend(c)
            else:
                out.append(c)
        return tuple(out)
    return (children,)


def create_element(
    type_: Any,
    props: Mapping[str, Any] | Any | None = None,
    *children: Any,
    **props_from_kwargs: Any,
) -> Element[Any, Mapping[str, Any]]:
    if props is None:
        props_dict = {}  # type: dict[str, Any]
    elif is_dataclass(props) and not isinstance(props, type):
        # NOTE: `dataclasses.asdict()` deep-copies values, which would break
        # identity-sensitive fields like `ref`. We want a shallow mapping.
        props_dict = {f.name: getattr(props, f.name) for f in fields(props)}
    else:
        props_dict = dict(props)  # type: ignore[arg-type]
    if props_from_kwargs:
        props_dict.update(props_from_kwargs)
    if children:
        props_dict["children"] = _normalize_children(children)
    elif "children" in props_dict:
        props_dict["children"] = _normalize_children(props_dict["children"])
    key = props_dict.pop("key", None)
    if key is not None:
        key = str(key)
    ref = props_dict.pop("ref", None)
    # Apply defaultProps for composite components, matching React behavior where
    # missing/undefined props fall back to defaults before lifecycles run.
    dp = getattr(type_, "defaultProps", None)
    if isinstance(dp, Mapping):
        for k, v in dp.items():
            if props_dict.get(k, None) is None:
                props_dict[k] = v
    _warn_if_illegal_fragment_props(type_, props_dict)
    _maybe_warn_host_children_keys(type_, props_dict.get("children", ()))
    return Element(type=type_, props=props_dict, key=key, ref=ref)


def clone_element(
    element: Element[Any, Any],
    props: Mapping[str, Any] | None = None,
    *children: Any,
    **props_from_kwargs: Any,
) -> Element[Any, Mapping[str, Any]]:
    """
    Shallow clone of an ``Element`` with merged props (React ``cloneElement``-like).

    ``key`` / ``ref`` from ``props`` / kwargs override the source element when present.
    """
    if element is None:
        raise TypeError("clone_element expected an Element but received None.")
    props_dict = dict(element.props)
    if props is not None:
        props_dict.update(dict(props))
    if props_from_kwargs:
        props_dict.update(props_from_kwargs)
    if children:
        props_dict["children"] = _normalize_children(children)
    elif "children" in props_dict:
        props_dict["children"] = _normalize_children(props_dict["children"])
    key = props_dict.pop("key", element.key)
    if key is not None:
        key = str(key)
    ref = props_dict.pop("ref", element.ref)
    _warn_if_illegal_fragment_props(element.type, props_dict)
    return Element(type=element.type, props=props_dict, key=key, ref=ref)


# Hyperscript-style alias (common in JS ecosystems; reads well in Python too).
h = create_element
