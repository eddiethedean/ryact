from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


def shallow_equal_props(a: dict[str, Any], b: dict[str, Any]) -> bool:
    if a.keys() != b.keys():
        return False
    return all(av == b[k] for k, av in a.items())


@dataclass(frozen=True)
class MemoType:
    inner: Any
    compare: Callable[[dict[str, Any], dict[str, Any]], bool] | None = None


def memo(
    component: Any, compare: Callable[[dict[str, Any], dict[str, Any]], bool] | None = None
) -> MemoType:
    return MemoType(inner=component, compare=compare)


@dataclass(frozen=True)
class ForwardRefType:
    render: Callable[[dict[str, Any], Any | None], Any]


def forward_ref(render: Callable[[dict[str, Any], Any | None], Any]) -> ForwardRefType:
    return ForwardRefType(render=render)
