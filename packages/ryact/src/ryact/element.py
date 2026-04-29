from __future__ import annotations

import warnings
from collections.abc import Mapping, Sequence
from types import MappingProxyType
from contextlib import contextmanager
from dataclasses import dataclass, fields, is_dataclass
from typing import Any, Generic, TypeVar, Union

from .dev import is_dev

TType = TypeVar("TType")
TProps = TypeVar("TProps", bound=Mapping[str, Any])


@dataclass(frozen=True)
class Element(Generic[TType, TProps]):
    type: TType
    props: TProps
    key: str | None = None
    ref: Any | None = None


ChildrenInput = Union[Sequence[Any], Any, None]

_FRAGMENT = "__fragment__"

_CURRENT_OWNER_STACK: list[str] = []


def _element_special_owner_label(type_: Any) -> str:
    if isinstance(type_, str):
        return type_
    return str(getattr(type_, "__name__", type_) or "Unknown")


class _ReadonlyDevElementProps(Mapping[str, Any]):
    """DEV: React-like frozen props + warnings when reading reserved ``key`` / ``ref``."""

    __slots__ = ("_data", "_owner")

    def __init__(self, data: dict[str, Any], *, owner: str) -> None:
        self._data = data
        self._owner = owner

    def __getitem__(self, key: str) -> Any:
        if key == "key":
            warnings.warn(
                f"{self._owner}: `key` is not a prop. Trying to access it will result "
                "in `None` being returned. If you need to access the same value within "
                "the child component, you should pass it as a different prop. "
                "(https://react.dev/link/special-props)",
                RuntimeWarning,
                stacklevel=2,
            )
            return None
        if key == "ref":
            warnings.warn(
                f"{self._owner}: `ref` is not a prop. Trying to access it will result "
                "in `None` being returned. If you need to access the same value within "
                "the child component, you should pass it as a different prop. "
                "(https://react.dev/link/special-props)",
                RuntimeWarning,
                stacklevel=2,
            )
            return None
        return self._data[key]

    def __iter__(self) -> Any:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __contains__(self, key: object) -> bool:
        return key in self._data


def _finalize_element_props(type_: Any, props_dict: dict[str, Any]) -> Mapping[str, Any]:
    if not is_dev():
        return props_dict
    return _ReadonlyDevElementProps(props_dict, owner=_element_special_owner_label(type_))


class _RenderPropsView(Mapping[str, Any]):
    """DEV: warn on ``props['key']`` / ``props['ref']`` inside composite renders."""

    __slots__ = ("_data", "_owner")

    def __init__(self, data: Mapping[str, Any], *, owner: str) -> None:
        self._data = data
        self._owner = owner

    def __getitem__(self, key: str) -> Any:
        if key == "key":
            warnings.warn(
                f"{self._owner}: `key` is not a prop. Trying to access it will result "
                "in `None` being returned. If you need to access the same value within "
                "the child component, you should pass it as a different prop. "
                "(https://react.dev/link/special-props)",
                RuntimeWarning,
                stacklevel=2,
            )
            return None
        if key == "ref":
            warnings.warn(
                f"{self._owner}: `ref` is not a prop. Trying to access it will result "
                "in `None` being returned. If you need to access the same value within "
                "the child component, you should pass it as a different prop. "
                "(https://react.dev/link/special-props)",
                RuntimeWarning,
                stacklevel=2,
            )
            return None
        return self._data[key]  # type: ignore[index]

    def __iter__(self) -> Any:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __contains__(self, key: object) -> bool:
        return key in self._data


def props_view_for_class_instance(inst: Any) -> Mapping[str, Any]:
    """Public ``this.props`` view for class components (DEV key/ref read warnings)."""
    raw = getattr(inst, "_props", None)
    if not isinstance(raw, dict):
        return MappingProxyType({})
    if not is_dev():
        return MappingProxyType(raw)
    return _RenderPropsView(raw, owner=_element_special_owner_label(type(inst)))


def props_for_component_render(type_: Any, props: Mapping[str, Any]) -> Mapping[str, Any]:
    """Props snapshot passed to class/function render paths (DEV key/ref read warnings)."""
    if not is_dev() or isinstance(type_, str):
        return props
    return _RenderPropsView(dict(props), owner=_element_special_owner_label(type_))


@contextmanager
def _with_current_owner(name: str | None) -> Any:
    if not name or not is_dev():
        yield
        return
    _CURRENT_OWNER_STACK.append(name)
    try:
        yield
    finally:
        try:
            _CURRENT_OWNER_STACK.pop()
        except Exception:
            pass


def _current_owner_display_name() -> str | None:
    if not is_dev() or not _CURRENT_OWNER_STACK:
        return None
    return _CURRENT_OWNER_STACK[-1]


def _maybe_warn_host_children_keys(
    type_: Any,
    children: tuple[Any, ...],
    *,
    static_jsxs_children: bool = False,
) -> None:
    if static_jsxs_children or not isinstance(type_, str) or not is_dev() or len(children) < 2:
        return
    from .children import warn_if_missing_keys

    owner = _current_owner_display_name()
    warn_if_missing_keys(children, stacklevel=3, parent_display_name=owner or str(type_))


def _warn_key_prop_in_spread_props_bag(type_: Any, *, stacklevel: int = 3) -> None:
    if not is_dev():
        return
    comp = _element_special_owner_label(type_)
    warnings.warn(
        'A props object containing a "key" prop is being spread into JSX:\n'
        "  let props = {key: someKey, prop: ...};\n\n"
        "React keys must be passed directly to JSX without using spread:\n"
        "  let props = {prop: ...};\n\n"
        f"  in {comp}",
        RuntimeWarning,
        stacklevel=stacklevel,
    )


def _maybe_warn_fragment_children_keys(type_: Any, children: tuple[Any, ...]) -> None:
    if type_ != _FRAGMENT or not is_dev() or len(children) < 2:
        return
    from .children import warn_if_duplicate_keys, warn_if_missing_keys

    warn_if_missing_keys(children, stacklevel=3, parent_display_name="Fragment")
    warn_if_duplicate_keys(children, stacklevel=3, parent_display_name="Fragment")


def _warn_if_illegal_fragment_props(type_: Any, props_dict: dict[str, Any]) -> None:
    if type_ != _FRAGMENT or not is_dev():
        return
    illegal = [k for k in props_dict if k != "children"]
    if not illegal:
        return
    warnings.warn(
        "Invalid prop(s) supplied to React.Fragment. "
        f"Only the children prop is supported; received: {', '.join(sorted(illegal))}.",
        UserWarning,
        stacklevel=2,
    )


def _normalize_children(children: ChildrenInput) -> tuple[Any, ...]:
    if children is None:
        return ()
    if isinstance(children, (list, tuple)):
        out = []  # type: list[Any]
        for c in children:
            if isinstance(c, (list, tuple)):
                out.extend(c)
            else:
                out.append(c)
        return tuple(out)
    return (children,)


def _create_element_impl(
    type_: Any,
    props: Mapping[str, Any] | Any | None,
    children_args: tuple[Any, ...],
    props_from_kwargs: dict[str, Any],
    *,
    static_jsxs_children: bool = False,
    jsx_runtime: bool = False,
) -> Element[Any, Mapping[str, Any]]:
    keys_from_kw = set(props_from_kwargs.keys())
    reused_identity = False
    if props is None:
        props_dict: dict[str, Any] = {}
    elif is_dataclass(props) and not isinstance(props, type):
        props_dict = {f.name: getattr(props, f.name) for f in fields(props)}
    elif isinstance(props, dict):
        props_dict = props
        reused_identity = True
    else:
        props_dict = dict(props)  # type: ignore[arg-type]

    if reused_identity and (props_from_kwargs or children_args):
        props_dict = dict(props_dict)
        reused_identity = False
    if props_from_kwargs:
        props_dict.update(props_from_kwargs)

    if children_args:
        props_dict["children"] = _normalize_children(children_args)
    elif "children" in props_dict:
        ch_raw = props_dict["children"]
        if static_jsxs_children and is_dev() and not isinstance(ch_raw, (list, tuple)):
            warnings.warn(
                "React.jsx: Static children should always be an array. "
                "You are likely explicitly calling React.jsxs or React.jsxDEV. "
                "Use the Babel transform instead.",
                RuntimeWarning,
                stacklevel=3,
            )
        props_dict["children"] = _normalize_children(ch_raw)

    if reused_identity and ("key" in props_dict or "ref" in props_dict):
        props_dict = dict(props_dict)
        reused_identity = False

    if jsx_runtime and is_dev() and "key" in props_dict and "key" not in keys_from_kw:
        _warn_key_prop_in_spread_props_bag(type_, stacklevel=4)

    key = props_dict.pop("key", None)
    if key is not None:
        key = str(key)
    ref = props_dict.pop("ref", None)
    if type_ == _FRAGMENT and ref is not None and is_dev():
        warnings.warn(
            "Invalid attribute `ref` supplied to React.Fragment.",
            UserWarning,
            stacklevel=2,
        )
    dp = getattr(type_, "defaultProps", None)
    if isinstance(dp, Mapping):
        for k, v in dp.items():
            if k not in props_dict:
                props_dict[k] = v
    _warn_if_illegal_fragment_props(type_, props_dict)
    _maybe_warn_host_children_keys(
        type_,
        props_dict.get("children", ()),
        static_jsxs_children=static_jsxs_children,
    )
    _maybe_warn_fragment_children_keys(type_, props_dict.get("children", ()))
    stored_props = _finalize_element_props(type_, props_dict)
    return Element(type=type_, props=stored_props, key=key, ref=ref)


def create_element(
    type_: Any,
    props: Mapping[str, Any] | Any | None = None,
    *children: Any,
    **props_from_kwargs: Any,
) -> Element[Any, Mapping[str, Any]]:
    return _create_element_impl(
        type_,
        props,
        children,
        dict(props_from_kwargs),
        static_jsxs_children=False,
        jsx_runtime=False,
    )


def jsx(
    type_: Any,
    props: Mapping[str, Any] | Any | None = None,
    *children: Any,
    **props_from_kwargs: Any,
) -> Element[Any, Mapping[str, Any]]:
    """React ``jsx`` analogue: DEV warns if ``key`` appears inside a props object (spread-style)."""
    return _create_element_impl(
        type_,
        props,
        children,
        dict(props_from_kwargs),
        static_jsxs_children=False,
        jsx_runtime=True,
    )


def jsxs(
    type_: Any,
    props: Mapping[str, Any] | Any | None = None,
    *children: Any,
    **props_from_kwargs: Any,
) -> Element[Any, Mapping[str, Any]]:
    """React ``jsxs`` analogue: static child list (skips missing-key warnings for sibling arrays)."""
    return _create_element_impl(
        type_,
        props,
        children,
        dict(props_from_kwargs),
        static_jsxs_children=True,
        jsx_runtime=True,
    )


def clone_element(
    element: Element[Any, Any],
    props: Mapping[str, Any] | None = None,
    *children: Any,
    **props_from_kwargs: Any,
) -> Element[Any, Mapping[str, Any]]:
    """
    Shallow clone of an ``Element`` with merged props (React ``cloneElement``-like).

    ``key`` / ``ref`` from ``props`` / kwargs override the source element when present.
    """
    if element is None or not isinstance(element, Element):
        raise TypeError("clone_element expected an Element.")
    props_dict = dict(element.props)
    if props is not None:
        props_dict.update(dict(props))
    if props_from_kwargs:
        props_dict.update(props_from_kwargs)
    if children:
        # Upstream: passing `undefined` as an explicit child argument overrides
        # existing children. Python analogue: `None` as a single explicit child
        # clears children.
        if len(children) == 1 and isinstance(children[0], (list, tuple)):
            # Warn for missing keys if an array/tuple of elements is passed as a
            # rest argument, matching the element validator/key warning surface.
            _maybe_warn_host_children_keys(element.type, tuple(children[0]))
        if len(children) == 1 and children[0] is None:
            props_dict["children"] = ()
        else:
            props_dict["children"] = _normalize_children(children)
    elif "children" in props_dict:
        props_dict["children"] = _normalize_children(props_dict["children"])
    key = props_dict.pop("key", element.key)
    if key is not None:
        key = str(key)
    ref = props_dict.pop("ref", element.ref)
    if element.type == _FRAGMENT and ref is not None and is_dev():
        warnings.warn(
            "Invalid attribute `ref` supplied to React.Fragment.",
            UserWarning,
            stacklevel=2,
        )
    dp2 = getattr(element.type, "defaultProps", None)
    if isinstance(dp2, Mapping):
        for k, v in dp2.items():
            if k not in props_dict:
                props_dict[k] = v
    _warn_if_illegal_fragment_props(element.type, props_dict)
    stored_props = _finalize_element_props(element.type, props_dict)
    return Element(type=element.type, props=stored_props, key=key, ref=ref)


def coerce_top_level_render_result(value: Any) -> Any:
    """
    React allows class/function components to return an array/iterable of children
    (top-level fragment) and nested arrays (implicit sub-fragments). Normalize to
    ``__fragment__`` elements for the reconciler and for server rendering.
    """
    if value is None or isinstance(value, (str, int, float, Element)):
        return value
    if isinstance(value, (list, tuple)) and not isinstance(value, (str, bytes, bytearray)):

        def _pack(x: Any) -> Any:
            if isinstance(x, (list, tuple)) and not isinstance(x, (str, bytes, bytearray)):
                return create_element(_FRAGMENT, {"children": tuple(_pack(i) for i in x)})
            return x

        packed = tuple(_pack(x) for x in value)
        # If a component returns a single child wrapped in an array/list, treat it as the
        # same as returning the child directly. This preserves identity when switching
        # between `child` and `[child]`.
        if len(packed) == 1 and not isinstance(packed[0], (list, tuple)):
            return packed[0]
        return create_element(_FRAGMENT, {"children": packed})
    return value


# Hyperscript-style alias (common in JS ecosystems; reads well in Python too).
h = create_element
