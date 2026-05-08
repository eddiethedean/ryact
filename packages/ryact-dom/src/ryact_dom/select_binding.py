# ``<select>`` / ``<option>`` binding (ReactDOMSelect parity subset).
from __future__ import annotations

import warnings
from collections.abc import Mapping, Sequence
from typing import Any

from ryact.concurrent import Fragment
from ryact.dev import is_dev
from ryact.element import Element, create_element


def _truthy_disabled(props: Mapping[str, Any]) -> bool:
    v = props.get("disabled")
    return v is True or v == "" or v == "disabled"


def _select_stringify(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if v is None:
        return ""
    return str(v)


def _option_element_value(opt: Element) -> str:
    if "value" in opt.props and opt.props["value"] is not None:
        return _select_stringify(opt.props["value"])
    parts: list[str] = []
    for t in _walk_text_nodes(opt.props.get("children", ())):
        parts.append(t)
    return "".join(parts)


def _walk_text_nodes(ch: Any) -> list[str]:
    if ch is None or ch is False:
        return []
    if isinstance(ch, (str, int, float)):
        return [str(ch)]
    if isinstance(ch, Sequence) and not isinstance(ch, (str, bytes, Element)):
        out: list[str] = []
        for x in ch:
            out.extend(_walk_text_nodes(x))
        return out
    if isinstance(ch, Element):
        if ch.type == Fragment:
            return _walk_text_nodes(ch.props.get("children", ()))
        out: list[str] = []
        for sub in ch.props.get("children", ()):
            out.extend(_walk_text_nodes(sub))
        return out
    return []


def iter_option_elements_in_select_children(children: Sequence[Any]) -> list[Element]:
    found: list[Element] = []
    for ch in children:
        if not isinstance(ch, Element) or not isinstance(ch.type, str):
            continue
        tl = ch.type.lower()
        if tl == "option":
            found.append(ch)
        elif tl == "optgroup":
            found.extend(iter_option_elements_in_select_children(ch.props.get("children", ())))
        elif ch.type == Fragment:
            found.extend(iter_option_elements_in_select_children(ch.props.get("children", ())))
    return found


def _warn_select_dev(
    *,
    raw: Mapping[str, Any],
    options: list[Element],
    multiple: bool,
) -> None:
    if not is_dev():
        return

    has_val = "value" in raw
    has_dv = "defaultValue" in raw or "default_value" in raw

    if has_val and raw.get("value") is None:
        if multiple:
            warnings.warn(
                "`value` prop on `select` should not be null. "
                "Consider using an empty array when `multiple` is "
                "set to `true` to clear the component or `undefined` "
                "for uncontrolled components.\n"
                "    in select",
                UserWarning,
                stacklevel=4,
            )
        else:
            warnings.warn(
                "`value` prop on `select` should not be null. "
                "Consider using an empty string to clear the component or `undefined` "
                "for uncontrolled components.\n"
                "    in select",
                UserWarning,
                stacklevel=4,
            )

    if has_val and has_dv:
        warnings.warn(
            "Select elements must be either controlled or uncontrolled "
            "(specify either the value prop, or the defaultValue prop, but not "
            "both). Decide between using a controlled or uncontrolled select "
            "element and remove one of these props. More info: "
            "https://react.dev/link/controlled-components\n"
            "    in select",
            UserWarning,
            stacklevel=4,
        )

    for opt in options:
        if "selected" in opt.props:
            warnings.warn(
                "Use the `defaultValue` or `value` props on `<select>` instead of "
                "setting `selected` on `<option>`.\n"
                "    in option",
                UserWarning,
                stacklevel=4,
            )
            break

    if (
        has_val
        and not raw.get("disabled")
        and "onChange" not in raw
        and "on_change" not in raw
    ):
        if raw.get("value") is not None:
            warnings.warn(
                "You provided a `value` prop to a form "
                "field without an `onChange` handler. This will render a read-only "
                "field. If the field should be mutable use `defaultValue`. "
                "Otherwise, set `onChange`.\n"
                "    in select",
                UserWarning,
                stacklevel=4,
            )


UNDEFINED_SENTINEL = object()


def _coerce_select_control_value(raw_val: Any, *, multiple: bool) -> set[str] | str | None:
    if raw_val is None or raw_val is UNDEFINED_SENTINEL:
        return None
    if multiple:
        if isinstance(raw_val, (str, bytes)):
            return {_select_stringify(raw_val)}
        try:
            it = iter(raw_val)
        except TypeError:
            return {_select_stringify(raw_val)}
        out: set[str] = set()
        for x in it:
            out.add(_select_stringify(x))
        return out
    return _select_stringify(raw_val)


def compute_option_selected_mask(
    *,
    raw: Mapping[str, Any],
    normalized_select_props: Mapping[str, Any],
    options: list[Element],
) -> list[bool]:
    multiple = bool(normalized_select_props.get("multiple"))
    size_gt_1 = False
    sz = normalized_select_props.get("size")
    if sz is not None:
        try:
            size_gt_1 = int(sz) > 1
        except (TypeError, ValueError):
            size_gt_1 = False

    has_val = "value" in raw
    has_dv = "defaultValue" in raw or "default_value" in raw
    raw_val = raw.get("value", UNDEFINED_SENTINEL)
    dv_raw = raw.get("defaultValue", raw.get("default_value", UNDEFINED_SENTINEL))

    opt_vals = [_option_element_value(o) for o in options]

    if has_val:
        coerced = _coerce_select_control_value(
            None if raw_val is UNDEFINED_SENTINEL else raw_val, multiple=multiple
        )
        if coerced is None:
            return [False] * len(options)
        if multiple and isinstance(coerced, set):
            return [v in coerced for v in opt_vals]
        assert isinstance(coerced, str)
        return [v == coerced for v in opt_vals]

    if has_dv and dv_raw is not UNDEFINED_SENTINEL:
        coerced = _coerce_select_control_value(dv_raw, multiple=multiple)
        if coerced is None:
            return [False] * len(options)
        if multiple and isinstance(coerced, set):
            return [v in coerced for v in opt_vals]
        assert isinstance(coerced, str)
        return [v == coerced for v in opt_vals]

    if multiple or size_gt_1:
        return [False] * len(options)

    mask = [False] * len(options)
    for i, o in enumerate(options):
        if not _truthy_disabled(o.props):
            mask[i] = True
            break
    return mask


def apply_select_binding_to_child_trees(
    children: Sequence[Any],
    selected_mask: list[bool],
) -> tuple[Any, ...]:
    mask_iter = iter(selected_mask)

    def _clone_option(opt: Element) -> Element:
        sel = next(mask_iter)
        p = dict(opt.props) if isinstance(opt.props, Mapping) else {}
        p.pop("selected", None)
        if sel:
            p["selected"] = True
        return create_element(opt.type, p, key=opt.key, ref=opt.ref)

    def _walk(chs: Sequence[Any]) -> list[Any]:
        out: list[Any] = []
        for ch in chs:
            if not isinstance(ch, Element) or not isinstance(ch.type, str):
                out.append(ch)
                continue
            tl = ch.type.lower()
            if tl == "option":
                out.append(_clone_option(ch))
            elif tl == "optgroup":
                sub = _walk(ch.props.get("children", ()))
                p2 = dict(ch.props) if isinstance(ch.props, Mapping) else {}
                p2["children"] = tuple(sub)
                out.append(create_element(ch.type, p2, key=ch.key, ref=ch.ref))
            elif ch.type == Fragment:
                sub = _walk(ch.props.get("children", ()))
                out.append(create_element(Fragment, {"children": tuple(sub)}, key=ch.key, ref=ch.ref))
            else:
                out.append(ch)
        return out

    return tuple(_walk(tuple(children)))


def process_select_element_children(
    raw_props: Mapping[str, Any],
    normalized_props: dict[str, Any],
    children: Sequence[Any],
) -> tuple[Any, ...]:
    opts = iter_option_elements_in_select_children(children)
    multiple = bool(normalized_props.get("multiple"))
    if is_dev():
        _warn_select_dev(raw=raw_props, options=opts, multiple=multiple)
    mask = compute_option_selected_mask(
        raw=raw_props,
        normalized_select_props=normalized_props,
        options=opts,
    )
    return apply_select_binding_to_child_trees(children, mask)


def strip_select_internal_props(props: dict[str, Any]) -> None:
    for k in ("value", "defaultValue", "default_value"):
        props.pop(k, None)
