from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Protocol


class InteropRunner(Protocol):
    def render_js(
        self,
        *,
        module_id: str,
        export: str,
        props: Mapping[str, object] | None,
        children: Sequence[object],
        boundary_id: str,
    ) -> object: ...

    def render_py(
        self,
        *,
        component_id: str,
        props: Mapping[str, object] | None,
        children: Sequence[object],
        boundary_id: str,
    ) -> object: ...


def _is_jsonish(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, (bool, int, float, str)):
        return True
    if isinstance(value, (list, tuple)):
        return all(_is_jsonish(v) for v in value)
    if isinstance(value, dict):
        return all(isinstance(k, str) and _is_jsonish(v) for k, v in value.items())
    return False


def validate_marshaled(value: object) -> None:
    if not _is_jsonish(value):
        raise TypeError(
            "Interop boundary only allows JSON-serializable values (None/bool/number/str/"
            "list/dict[str,...]) in stub mode."
        )


@dataclass
class StubInteropRunner:
    _js: dict[tuple[str, str], Callable[[Mapping[str, object] | None, Sequence[object]], object]] = field(
        default_factory=dict
    )
    _py: dict[str, Callable[[Mapping[str, object] | None, Sequence[object]], object]] = field(default_factory=dict)

    def register_js(
        self,
        *,
        module_id: str,
        export: str = "default",
        fn: Callable[[Mapping[str, object] | None, Sequence[object]], object],
    ) -> None:
        self._js[(module_id, export)] = fn

    def register_py(
        self,
        *,
        component_id: str,
        fn: Callable[[Mapping[str, object] | None, Sequence[object]], object],
    ) -> None:
        self._py[component_id] = fn

    def render_js(
        self,
        *,
        module_id: str,
        export: str,
        props: Mapping[str, object] | None,
        children: Sequence[object],
        boundary_id: str,
    ) -> object:
        validate_marshaled(props if props is not None else {})
        validate_marshaled(list(children))
        key = (module_id, export)
        if key not in self._js:
            raise KeyError(f"Unregistered JS module export for boundary {boundary_id}: {key!r}")
        return self._js[key](props, children)

    def render_py(
        self,
        *,
        component_id: str,
        props: Mapping[str, object] | None,
        children: Sequence[object],
        boundary_id: str,
    ) -> object:
        validate_marshaled(props if props is not None else {})
        validate_marshaled(list(children))
        if component_id not in self._py:
            raise KeyError(f"Unregistered Python component for boundary {boundary_id}: {component_id!r}")
        return self._py[component_id](props, children)
