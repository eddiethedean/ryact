from __future__ import annotations

import warnings
from collections.abc import Callable, Mapping
from typing import Any

from .component import Component


def _effective_spec(spec: Mapping[str, Any]) -> dict[str, Any]:
    mixins = spec.get("mixins")
    if mixins is None:
        return dict(spec)
    if not isinstance(mixins, list):
        warnings.warn(
            "mixins are not supported",
            RuntimeWarning,
            stacklevel=3,
        )
        return dict(spec)
    if any(not isinstance(m, dict) for m in mixins):
        warnings.warn(
            "mixins are not supported",
            RuntimeWarning,
            stacklevel=3,
        )
        return dict(spec)
    merged: dict[str, Any] = {}
    for m in mixins:
        merged.update(m)
    for k, v in spec.items():
        if k != "mixins":
            merged[k] = v
    return merged


class _CreateReactClassMeta(type(Component)):
    """Block direct `Component()` calls; the reconciler constructs via ``__new__``/``__init__``."""

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        warnings.warn(
            "Something is calling a React component directly. Use a factory or JSX instead. "
            "See: https://fb.me/react-legacyfactory",
            RuntimeWarning,
            stacklevel=2,
        )
        raise TypeError("Legacy factory calls are not supported.")


def create_react_class(spec: Mapping[str, Any]) -> type[Component]:
    """
    Minimal create-react-class compatibility helper.

    This is intentionally tiny: enough to start translating the upstream integration suite
    as pending-first work (no autobind/classic APIs yet).
    """
    if not isinstance(spec, Mapping):
        raise TypeError("create_react_class(spec) expects a mapping.")
    effective = _effective_spec(spec)
    render = effective.get("render")
    if not callable(render):
        raise TypeError("create_react_class(spec) requires a callable `render`.")

    # DEV warnings for common legacy create-react-class mistakes (subset).
    if "componentWillRecieveProps" in effective:
        warnings.warn(
            "Did you mean componentWillReceiveProps?",
            RuntimeWarning,
            stacklevel=2,
        )
    if "UNSAFE_componentWillRecieveProps" in effective:
        warnings.warn(
            "Did you mean UNSAFE_componentWillReceiveProps?",
            RuntimeWarning,
            stacklevel=2,
        )
    if "shouldComponentUpdat" in effective:
        warnings.warn(
            "Did you mean shouldComponentUpdate?",
            RuntimeWarning,
            stacklevel=2,
        )

    _handled_spec_keys: set[str] = set()

    class C(Component, metaclass=_CreateReactClassMeta):
        def __init__(self, **props: Any) -> None:
            self._ryact_mounted = False
            super().__init__(**props)
            init = effective.get("getInitialState")
            if callable(init):
                st = init(self)
                if st is None:
                    return
                if not isinstance(st, dict):
                    raise TypeError("getInitialState() must return a dict or None.")
                self._state.update(st)  # type: ignore[attr-defined]

        def isMounted(self) -> bool:  # noqa: N802
            from .dev import is_dev

            if is_dev():
                label = getattr(type(self), "displayName", None) or type(self).__name__
                if not isinstance(label, str):
                    label = type(self).__name__
                warnings.warn(
                    f"Warning: {label}: isMounted is deprecated. Instead, make sure to "
                    "clean up subscriptions and pending requests in componentWillUnmount "
                    "to prevent memory leaks.",
                    RuntimeWarning,
                    stacklevel=2,
                )
            return bool(self._ryact_mounted)

        def render(self) -> Any:
            return render(self)

    name = effective.get("displayName")
    if isinstance(name, str) and name:
        C.__name__ = name
        C.displayName = name

    for key in (
        "componentDidMount",
        "componentDidUpdate",
        "componentWillUnmount",
        "shouldComponentUpdate",
        "getSnapshotBeforeUpdate",
        "getChildContext",
        "componentWillMount",
        "UNSAFE_componentWillMount",
        "componentWillReceiveProps",
        "UNSAFE_componentWillReceiveProps",
        "componentWillUpdate",
        "UNSAFE_componentWillUpdate",
    ):
        _handled_spec_keys.add(key)
        v = effective.get(key)
        if callable(v):
            setattr(C, key, v)

    gdsfp = effective.get("getDerivedStateFromProps")
    _handled_spec_keys.add("getDerivedStateFromProps")
    if callable(gdsfp):
        setattr(C, "getDerivedStateFromProps", staticmethod(gdsfp))
    gdsfe = effective.get("getDerivedStateFromError")
    _handled_spec_keys.add("getDerivedStateFromError")
    if callable(gdsfe):
        setattr(C, "getDerivedStateFromError", staticmethod(gdsfe))

    reserved_extra = {
        "render",
        "getInitialState",
        "mixins",
        "statics",
        "displayName",
        "childContextTypes",
        "contextTypes",
        "propTypes",
        "defaultProps",
    }
    for key, val in effective.items():
        if key in _handled_spec_keys or key in reserved_extra:
            continue
        if callable(val):
            setattr(C, key, val)

    if "childContextTypes" in effective:
        if not isinstance(effective.get("childContextTypes"), dict):
            raise TypeError("childContextTypes must be a dict.")
        setattr(C, "childContextTypes", effective["childContextTypes"])
    if "contextTypes" in effective:
        if not isinstance(effective.get("contextTypes"), dict):
            warnings.warn("Invalid contextTypes.", RuntimeWarning, stacklevel=2)
        else:
            setattr(C, "contextTypes", effective["contextTypes"])
    if isinstance(effective.get("defaultProps"), dict):
        setattr(C, "defaultProps", effective["defaultProps"])
    if "propTypes" in effective:
        if not isinstance(effective.get("propTypes"), dict):
            warnings.warn("Invalid propTypes.", RuntimeWarning, stacklevel=2)
        else:
            setattr(C, "propTypes", effective["propTypes"])

    statics = effective.get("statics")
    if statics is not None:
        if not isinstance(statics, dict):
            raise TypeError("statics must be a dict.")
        reserved = {"render", "getInitialState", "getChildContext", "statics"}
        for k, v in statics.items():
            if k in reserved:
                raise TypeError("Reserved property in statics.")
            setattr(C, k, v)

    return C
