from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _display_name(type_: Any) -> str:
    if type_ is None:
        return "Unknown"
    if isinstance(type_, str):
        # Host element tag or internal wrapper sentinel.
        return type_
    return getattr(type_, "__name__", repr(type_))


def format_component_stack(frames: list[str]) -> str:
    if not frames:
        return ""
    # Deterministic, React-ish shape (without file/line until later milestones).
    lines = ["Component stack:"]
    for name in frames:
        lines.append(f"  in {name}")
    return "\n".join(lines)


def component_stack_from_fiber(fiber: Any) -> str:
    """
    Best-effort component stack from a Fiber-like object.

    Expected shape (as in `ryact.reconciler.Fiber`): `.type` and `.parent`.
    """
    frames: list[str] = []
    cur = fiber
    while cur is not None:
        t = getattr(cur, "type", None)
        name = _display_name(t)
        # Skip synthetic root wrapper.
        if name not in ("__root__",):
            frames.append(name)
        cur = getattr(cur, "parent", None)
    return format_component_stack(frames)


@dataclass(frozen=True)
class DebugNode:
    type: str
    key: str | None
    children: list[DebugNode]


def inspect_fiber_tree(root: Any) -> DebugNode | None:
    """
    Minimal inspection hook surface (no UI).

    For now this is noop/None unless the passed object looks like a reconciler Root
    with a `.current` Fiber.
    """
    current = getattr(root, "current", None)
    if current is None:
        return None

    def walk(f: Any) -> DebugNode:
        kids: list[DebugNode] = []
        c = getattr(f, "child", None)
        while c is not None:
            kids.append(walk(c))
            c = getattr(c, "sibling", None)
        return DebugNode(
            type=_display_name(getattr(f, "type", None)), key=getattr(f, "key", None), children=kids
        )

    return walk(current)
