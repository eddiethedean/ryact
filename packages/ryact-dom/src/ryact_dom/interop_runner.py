from __future__ import annotations

import importlib.util
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType

from ryact_testkit.interop import InteropRunner, validate_marshaled


def _load_module_from_path(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module from {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@dataclass
class DomInteropRunner(InteropRunner):
    """
    Minimal host interop runner for `ryact-dom`.

    This executes "JS lane" compiled output as Python modules (produced by the TSX toolchain),
    and executes "Py lane" components via a registry of callables.
    """

    module_registry: dict[str, Path] = field(default_factory=dict)
    py_registry: dict[str, Callable[[Mapping[str, object] | None, Sequence[object]], object]] = (
        field(default_factory=dict)
    )
    scope: dict[str, object] = field(default_factory=dict)

    def register_module(self, *, module_id: str, path: Path) -> None:
        self.module_registry[module_id] = path

    def register_py(
        self,
        *,
        component_id: str,
        fn: Callable[[Mapping[str, object] | None, Sequence[object]], object],
    ) -> None:
        self.py_registry[component_id] = fn

    def render_js(
        self,
        *,
        module_id: str,
        export: str,
        props: Mapping[str, object] | None,
        children: Sequence[object],
        boundary_id: str,
    ) -> object:
        _ = export
        validate_marshaled(props if props is not None else {})
        validate_marshaled(list(children))
        if module_id not in self.module_registry:
            raise KeyError(f"Unregistered module_id for boundary {boundary_id}: {module_id!r}")
        mod = _load_module_from_path(self.module_registry[module_id])
        render = getattr(mod, "render", None)
        if not callable(render):
            raise TypeError(f"Module {module_id!r} has no callable render(scope) entrypoint")
        # Provide variables used by compiled TSX expressions.
        local_scope = dict(self.scope)
        if props is not None:
            local_scope.update(dict(props))
        local_scope["children"] = tuple(children)
        return render(local_scope)

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
        if component_id not in self.py_registry:
            raise KeyError(
                f"Unregistered python component for boundary {boundary_id}: {component_id!r}"
            )
        return self.py_registry[component_id](props, children)
