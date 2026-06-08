from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any

from .dom import ElementNode, Node


@dataclass
class RyactFormData:
    """Minimal ``FormData`` subset for React form actions."""

    _entries: dict[str, Any] = field(default_factory=dict)
    _submitter: ElementNode | None = None

    def get(self, name: str, default: Any = None) -> Any:
        if name not in self._entries:
            return default
        return self._entries[name]

    def delete(self, name: str) -> None:
        self._entries.pop(name, None)

    def set(self, name: str, value: Any) -> None:
        self._entries[name] = value

    def __iter__(self) -> Iterator[tuple[str, Any]]:
        return iter(self._entries.items())


def _input_value_for_formdata(node: ElementNode) -> str | None:
    tl = node.tag.lower()
    if tl != "input":
        return None
    t = str(node.props.get("type", "text")).lower()
    if t in ("submit", "button", "image", "reset"):
        return None
    if t in ("checkbox", "radio") and not node.checked:
        return None
    return node.dom_input_value()


def _collect_named_fields(form: ElementNode, *, submitter: ElementNode | None) -> RyactFormData:
    fd = RyactFormData(_submitter=submitter)
    exclude_submitter_name = submitter is not None and _submitter_uses_function_action(submitter)

    def walk(n: Node) -> None:
        if not isinstance(n, ElementNode):
            return
        if n.tag.lower() == "input":
            name = n.props.get("name")
            if name is not None and str(name) != "":
                if exclude_submitter_name and submitter is not None and n is submitter:
                    pass
                else:
                    val = _input_value_for_formdata(n)
                    if val is not None:
                        fd._entries[str(name)] = val
        for ch in n.children:
            walk(ch)

    walk(form)
    if submitter is not None:
        _append_submitter_fields(fd, submitter, exclude_name=exclude_submitter_name)
    return fd


def _submitter_uses_function_action(submitter: ElementNode) -> bool:
    fn = getattr(submitter, "_form_action_fn", None)
    return callable(fn)


def _append_submitter_fields(fd: RyactFormData, submitter: ElementNode, *, exclude_name: bool) -> None:
    tl = submitter.tag.lower()
    if tl not in ("button", "input"):
        return
    t = str(submitter.props.get("type", "")).lower() if tl == "input" else ""
    if tl == "input" and t not in ("submit", "image"):
        return
    if not exclude_name:
        name = submitter.props.get("name")
        if name is not None and str(name) != "":
            fd._entries[str(name)] = str(name)
    if t == "image" or (tl == "input" and t == "image"):
        base = str(submitter.props.get("name") or "submit")
        fd._entries[f"{base}.x"] = "0"
        fd._entries[f"{base}.y"] = "0"


def build_form_data(form: ElementNode, submitter: ElementNode | None = None) -> RyactFormData:
    """Collect fields for a form host node (descendants + optional submitter)."""

    return _collect_named_fields(form, submitter=submitter)


def inputs_associated_with_form(form: ElementNode) -> list[ElementNode]:
    """Inputs linked via ``form`` attribute (id match) or nested under the form."""

    form_id = form.props.get("id")
    out: list[ElementNode] = []

    def walk(n: Node, under_form: bool) -> None:
        if not isinstance(n, ElementNode):
            return
        if n.tag.lower() == "form":
            if n is not form:
                return
            under_form = True
        linked = under_form or (form_id is not None and str(n.props.get("form", "")) == str(form_id))
        if linked and n.tag.lower() == "input":
            out.append(n)
        for ch in n.children:
            walk(ch, under_form)

    root = form
    while root.parent is not None:
        root = root.parent
    walk(root, under_form=False)
    return out


class FormElementsCollection:
    """Minimal ``HTMLFormElement.elements`` named access for tests."""

    def __init__(self, form: ElementNode) -> None:
        self._form = form
        self._by_name: dict[str, ElementNode] = {}
        for inp in inputs_associated_with_form(form):
            name = inp.props.get("name") or inp.props.get("id")
            if name is not None:
                self._by_name[str(name)] = inp
        for n, node in _walk_named_descendants(form).items():
            self._by_name.setdefault(n, node)

    def __getitem__(self, name: str) -> ElementNode:
        return self._by_name[name]

    def __getattr__(self, name: str) -> ElementNode:
        if name.startswith("_"):
            raise AttributeError(name)
        return self._by_name[name]


def _walk_named_descendants(form: ElementNode) -> Mapping[str, ElementNode]:
    out: dict[str, ElementNode] = {}

    def walk(n: Node) -> None:
        if not isinstance(n, ElementNode):
            return
        if n is not form and n.tag.lower() == "form":
            return
        name = n.props.get("name")
        if name is not None and str(name) != "":
            out[str(name)] = n
        for ch in n.children:
            walk(ch)

    for ch in form.children:
        walk(ch)
    return out


def coerce_form_action_value(value: Any) -> Callable[..., Any] | str | None:
    """Coerce ``action`` / ``formAction`` like React (functions kept; bool/symbol → null)."""

    if callable(value):
        return value
    if value is None:
        return None
    if isinstance(value, (str, int, float)):
        return str(value)
    if isinstance(value, (bool, type)):
        return None
    # Symbols and other exotic values → null
    try:
        import types

        if isinstance(value, types.FunctionType):
            return value
    except Exception:
        pass
    return None
