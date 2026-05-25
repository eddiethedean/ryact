from __future__ import annotations

from collections.abc import Callable

from ryact.element import Element

from .dom import Container
from .root import Root, create_root


def legacy_render(
    element: Element | None,
    container: Container,
    callback: Callable[[], None] | None = None,
) -> Root:
    """Legacy ``ReactDOM.render`` subset (mount callback validation only)."""

    if callback is not None and not callable(callback):
        raise TypeError(
            "ReactDOM.render(...): Expected the last optional `callback` argument to be a function."
        )
    root = create_root(container)
    root.render(element)
    if callback is not None:
        callback()
    return root
