from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _display_name(type_: Any) -> str:
    if type_ is None:
        return "Unknown"
    if isinstance(type_, str):
        # Host element tag or internal wrapper sentinel.
        if type_ == "__suspense__":
            return "Suspense"
        if type_ == "__offscreen__":
            return "Activity"
        if type_ == "__fragment__":
            return "Fragment"
        if type_ == "__strict_mode__":
            return "StrictMode"
        return type_
    # Built-in wrappers implemented as callable instances.
    if type(type_).__name__ == "LazyComponent":
        return "Lazy"
    # Wrapper dataclasses.
    if type(type_).__name__ == "ForwardRefType":
        render = getattr(type_, "render", None)
        render_name = getattr(render, "__name__", None)
        display = getattr(type_, "displayName", None)
        if isinstance(render_name, str) and render_name not in ("<lambda>", "render", ""):
            return render_name
        if isinstance(display, str) and display:
            return display
        return ""
    if type(type_).__name__ == "MemoType":
        inner = getattr(type_, "inner", None)
        inner_name = getattr(inner, "__name__", None)
        if isinstance(inner_name, str) and inner_name:
            return inner_name
        return "Memo"
    if type(type_).__name__ == "ContextConsumerMarker":
        return "Context.Consumer"
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
        if name and name not in ("__root__",):
            frames.append(name)
        cur = getattr(cur, "parent", None)
    return format_component_stack(frames)


@dataclass(frozen=True)
class DebugNode:
    type: str
    key: str | None
    children: list[DebugNode]
    props: dict[str, Any] | None = None
    state: dict[str, Any] | None = None
    hook_types: list[str] | None = None
    debug_values: list[str] | None = None


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
        props = getattr(f, "memoized_props", None) or getattr(f, "pending_props", None)
        props_out: dict[str, Any] | None = None
        if isinstance(props, dict):
            props_out = dict(props)
        state_out: dict[str, Any] | None = None
        inst = getattr(f, "state_node", None)
        st = getattr(inst, "_state", None) if inst is not None else None
        if isinstance(st, dict):
            state_out = dict(st)
        hook_types: list[str] | None = None
        debug_vals: list[str] | None = None
        hooks = getattr(f, "hooks", None)
        if isinstance(hooks, list):
            hook_types = [type(h).__name__ for h in hooks]
            dv = [
                str(getattr(h, "label", "")) for h in hooks if type(h).__name__ == "_DebugValueHook"
            ]
            if dv:
                debug_vals = dv
        return DebugNode(
            type=_display_name(getattr(f, "type", None)),
            key=getattr(f, "key", None),
            props=props_out,
            state=state_out,
            hook_types=hook_types,
            debug_values=debug_vals,
            children=kids,
        )

    return walk(current)
