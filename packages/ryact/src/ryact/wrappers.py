from __future__ import annotations

import inspect
import warnings
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .dev import is_dev


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
    displayName: str | None = None


def forward_ref(render: Callable[[dict[str, Any], Any | None], Any]) -> ForwardRefType:
    if not callable(render):
        if is_dev():
            warnings.warn(
                "forward_ref() expects a render function but received a non-callable.",
                RuntimeWarning,
                stacklevel=2,
            )
        # Let the reconciler throw if this is used.
        return ForwardRefType(render=render)  # type: ignore[arg-type]
    if is_dev():
        # React validates render function signature in DEV.
        try:
            sig = inspect.signature(render)
            params = [
                p
                for p in sig.parameters.values()
                if p.kind
                not in (
                    inspect.Parameter.VAR_POSITIONAL,
                    inspect.Parameter.VAR_KEYWORD,
                )
            ]
            arity = len(params)
            if arity > 2:
                warnings.warn(
                    "forwardRef render functions accept exactly two parameters: props and ref.",
                    RuntimeWarning,
                    stacklevel=2,
                )
            elif arity == 1:
                warnings.warn(
                    "forwardRef render functions should accept two parameters: props and ref.",
                    RuntimeWarning,
                    stacklevel=2,
                )
        except Exception:
            pass
        if getattr(render, "defaultProps", None) is not None:
            warnings.warn(
                "forwardRef render functions do not support defaultProps.",
                RuntimeWarning,
                stacklevel=2,
            )
        if isinstance(render, MemoType):
            warnings.warn(
                "forwardRef requires a render function; did you mean memo(forwardRef(...))?",
                RuntimeWarning,
                stacklevel=2,
            )
    return ForwardRefType(render=render)
