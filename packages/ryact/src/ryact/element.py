from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
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


def create_element(type_: Any, props: Mapping[str, Any] | None = None, *children: Any) -> Element:
    props_dict = dict(props or {})  # type: Dict[str, Any]
    if children:
        props_dict["children"] = _normalize_children(children)
    key = props_dict.pop("key", None)
    ref = props_dict.pop("ref", None)
    return Element(type=type_, props=props_dict, key=key, ref=ref)
