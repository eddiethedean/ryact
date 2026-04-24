from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .element import create_element

JSSubtree = "__js_subtree__"
PySubtree = "__py_subtree__"


def js_subtree(
    *,
    module_id: str,
    export: str = "default",
    props: Mapping[str, object] | None = None,
    children: Sequence[object] = (),
    key: str | None = None,
) -> Any:
    """
    Explicit interop boundary: Python-authored tree embeds a foreign (JS/TSX) subtree.

    Execution is host-owned; in stub mode the host uses a deterministic runner.
    """
    return create_element(
        JSSubtree,
        {
            "module_id": module_id,
            "export": export,
            "props": dict(props) if props is not None else None,
            "children": tuple(children),
            "key": key,
        },
    )


def py_subtree(
    *,
    component_id: str,
    props: Mapping[str, object] | None = None,
    children: Sequence[object] = (),
    key: str | None = None,
) -> Any:
    """
    Explicit interop boundary: toolchain-authored tree embeds a foreign Python subtree.

    Execution is host-owned; in stub mode the host uses a deterministic runner.
    """
    return create_element(
        PySubtree,
        {
            "component_id": component_id,
            "props": dict(props) if props is not None else None,
            "children": tuple(children),
            "key": key,
        },
    )
