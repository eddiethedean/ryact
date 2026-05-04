from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from .component import Component


def create_react_class(spec: Mapping[str, Any]) -> type[Component]:
    """
    Minimal create-react-class compatibility helper.

    This is intentionally tiny: enough to start translating the upstream integration suite
    as pending-first work (no mixins/autobind/classic APIs yet).
    """
    if not isinstance(spec, Mapping):
        raise TypeError("create_react_class(spec) expects a mapping.")
    render = spec.get("render")
    if not callable(render):
        raise TypeError("create_react_class(spec) requires a callable `render`.")

    class C(Component):
        def __init__(self, **props: Any) -> None:
            super().__init__(**props)
            init = spec.get("getInitialState")
            if callable(init):
                st = init(self)
                if isinstance(st, dict):
                    self._state.update(st)  # type: ignore[attr-defined]

        def render(self) -> Any:
            return render(self)

    name = spec.get("displayName")
    if isinstance(name, str) and name:
        C.__name__ = name

    # Copy known lifecycle members if provided.
    for key in (
        "componentDidMount",
        "componentDidUpdate",
        "componentWillUnmount",
        "shouldComponentUpdate",
        "getChildContext",
    ):
        v = spec.get(key)
        if callable(v):
            setattr(C, key, v)
    # Legacy context types.
    if isinstance(spec.get("childContextTypes"), dict):
        setattr(C, "childContextTypes", spec["childContextTypes"])
    if isinstance(spec.get("contextTypes"), dict):
        setattr(C, "contextTypes", spec["contextTypes"])
    if isinstance(spec.get("defaultProps"), dict):
        setattr(C, "defaultProps", spec["defaultProps"])

    return C

