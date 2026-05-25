from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .dom import ElementNode

_preserved_focus_host: ElementNode | None = None
_focused_host: ElementNode | None = None


def reset_host_focus_state() -> None:
    global _preserved_focus_host, _focused_host
    _preserved_focus_host = None
    _focused_host = None


def note_host_focused(host: ElementNode) -> None:
    global _focused_host
    _focused_host = host


def note_host_blurred(host: ElementNode) -> None:
    global _focused_host
    if _focused_host is host:
        _focused_host = None


def preserve_focus_before_commit(active: ElementNode | None = None) -> None:
    global _preserved_focus_host, _focused_host
    target = active if active is not None else _focused_host
    if target is not None:
        _preserved_focus_host = target


def restore_preserved_focus(host: ElementNode | None) -> None:
    """Re-focus a host that had focus before the last commit (React ``preserves focus``)."""

    global _preserved_focus_host
    if _preserved_focus_host is None or host is None:
        return
    if host is _preserved_focus_host or _is_same_host(host, _preserved_focus_host):
        host.focus()
    _preserved_focus_host = None


def restore_preserved_focus_in_container(root: object) -> None:
    """Find the preserved host in ``container.root`` and restore focus."""

    global _preserved_focus_host
    if _preserved_focus_host is None:
        return
    pinned_id = _preserved_focus_host._host_reconcile_id
    from .dom import Container, ElementNode, Node

    if not isinstance(root, Container):
        return
    container = root

    def walk(n: Node) -> ElementNode | None:
        if isinstance(n, ElementNode):
            if n._host_reconcile_id == pinned_id:
                return n
            for ch in n.children:
                got = walk(ch)
                if got is not None:
                    return got
        return None

    for ch in container.root.children:
        got = walk(ch)
        if got is not None:
            restore_preserved_focus(got)
            return


def _is_same_host(a: ElementNode, b: ElementNode) -> bool:
    return a._host_reconcile_id == b._host_reconcile_id and a.tag == b.tag


def autofocus_host_if_needed(host: ElementNode) -> None:
    if host.props.get("autoFocus") is True or host.props.get("autofocus") is True:
        host.focus()
