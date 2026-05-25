"""DEV warning suffix helpers (ReactDOMComponent source-ref parity)."""
from __future__ import annotations


def dev_in_host_line(tag: str) -> str:
    """Single host line with React DEV source-ref placeholder."""

    return f"    in {tag} (at **)"


def react_dev_owner_stack_suffix(owner_stack: str) -> str:
    """Component stack lines only (no host tag), each with ``(at **)``."""

    lines: list[str] = []
    if owner_stack and "Component stack:" in owner_stack:
        for part in owner_stack.splitlines():
            part = part.strip()
            if part.startswith("in "):
                lines.append(f"    {part} (at **)")
    return "\n".join(lines)


def react_dev_in_suffix(*, host_tag: str, owner_stack: str = "") -> str:
    """Trailing ``in … (at **)`` lines for console error parity."""

    lines = [dev_in_host_line(host_tag)]
    owner_lines = react_dev_owner_stack_suffix(owner_stack)
    if owner_lines:
        lines.append(owner_lines)
    return "\n".join(lines)
