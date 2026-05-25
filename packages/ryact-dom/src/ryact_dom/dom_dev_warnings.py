"""DEV warning suffix helpers (ReactDOMComponent source-ref parity)."""
from __future__ import annotations


def react_dev_in_suffix(*, host_tag: str, owner_stack: str = "") -> str:
    """Trailing ``in … (at **)`` lines for console error parity."""

    lines = [f"    in {host_tag} (at **)"]
    if owner_stack and "Component stack:" in owner_stack:
        for part in owner_stack.splitlines():
            part = part.strip()
            if part.startswith("in "):
                lines.append(f"    {part} (at **)")
    return "\n".join(lines)
