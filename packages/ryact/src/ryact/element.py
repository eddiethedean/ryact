from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, is_dataclass
from typing import Any, Union


@dataclass(frozen=True)
class Element:
    type: Any
    props: Mapping[str, Any]
    key: str | None = None
    ref: Any | None = None


ChildrenInput = Union[Sequence[Any], Any, None]


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
) -> Element:
    if props is None:
        props_dict = {}  # type: dict[str, Any]
    elif is_dataclass(props) and not isinstance(props, type):
        props_dict = asdict(props)
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
    return Element(type=type_, props=props_dict, key=key, ref=ref)


# Hyperscript-style alias (common in JS ecosystems; reads well in Python too).
h = create_element
