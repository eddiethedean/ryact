from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any


def cx(*values: Any) -> str:
    """
    Join truthy class fragments into a single class string.

    Intended for Pythonic authoring; renderer normalization still handles
    `class` / `className` / `class_name` merging.
    """

    parts: list[str] = []
    for v in values:
        if v is None or v is False:
            continue
        s = str(v).strip()
        if not s:
            continue
        parts.append(s)
    return " ".join(parts)


def style(**kwargs: Any) -> dict[str, Any]:
    """Construct a style dict (host-specific; passed through to the renderer)."""
    return dict(kwargs)


def style_dict(mapping: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize a mapping into a style dict (host-specific)."""
    return dict(mapping)


def on(event: str, handler: Callable[..., Any]) -> dict[str, Any]:
    """
    Build a Pythonic event listener prop dict.

    Example: `on("click", fn)` -> `{"on_click": fn}`
    """

    event = event.strip().lower().replace("-", "_")
    return {f"on_{event}": handler}
