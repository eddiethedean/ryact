# ``<select>`` / ``<option>`` binding (ReactDOMSelect parity subset).
from __future__ import annotations

import warnings
from collections.abc import Mapping, Sequence
from typing import Any

from ryact.concurrent import Fragment
from ryact.dev import is_dev
from ryact.element import UNDEFINED, Element, create_element

from .dom import ElementNode, TextNode


def _truthy_disabled(props: Mapping[str, Any]) -> bool:
    v = props.get("disabled")
    return v is True or v == "" or v == "disabled"


def _select_stringify(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if v is None:
        return ""
    return str(v)


def _prop_present(raw: Mapping[str, Any], key: str) -> bool:
    if key not in raw:
        return False
    return raw[key] is not UNDEFINED


def _invalid_option_host_value(v: Any) -> bool:
    if callable(v) and not isinstance(v, type):
        return True
    return type(v).__name__ == "Symbol"


def _option_label_text(opt: Element) -> str:
    parts: list[str] = []
    for t in _walk_text_nodes(opt.props.get("children", ())):
        parts.append(t)
    return "".join(parts)


def _option_element_value(opt: Element) -> str:
    if not _prop_present(opt.props, "value"):
        return _option_label_text(opt)
    v = opt.props["value"]
    if v is None:
        return _option_label_text(opt)
    if _invalid_option_host_value(v):
        if is_dev():
            warnings.warn(
                "Invalid value for prop `value` on tag. "
                "Either remove it from the element, or pass a string or number value to "
                "keep it in the DOM. For details, see https://react.dev/link/attribute-behavior \n"
                "    in option",
                UserWarning,
                stacklevel=4,
            )
        return _option_label_text(opt)
    try:
        return _select_stringify(v)
    except Exception as e:
        if is_dev():
            tn = type(v).__name__
            warnings.warn(
                f"The provided `value` attribute is an unsupported type {tn}. "
                "This value must be coerced to a string before using it here.\n"
                "    in option",
                UserWarning,
                stacklevel=4,
            )
        if isinstance(e, TypeError) and e.args:
            raise TypeError(e.args[0]) from e
        raise TypeError("prod message") from e


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
        elif tl == "optgroup" or ch.type == Fragment:
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

    has_val = _prop_present(raw, "value")
    has_dv = _prop_present(raw, "defaultValue") or _prop_present(raw, "default_value")

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
        and raw["value"] is not None
    ):
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


def _validate_select_form_coercion(v: Any) -> None:
    if v is None or v is UNDEFINED_SENTINEL:
        return
    if isinstance(v, (list, tuple)):
        for x in v:
            _validate_select_form_coercion(x)
        return
    if isinstance(v, (str, int, float, bool)):
        return
    try:
        str(v)
    except Exception as e:
        if is_dev():
            tn = type(v).__name__
            warnings.warn(
                "Form field values (value, checked, defaultValue, or defaultChecked props)"
                f" must be strings, not {tn}. "
                "This value must be coerced to a string before using it here.\n"
                "    in select",
                UserWarning,
                stacklevel=5,
            )
        if isinstance(e, TypeError) and e.args:
            raise TypeError(e.args[0]) from e
        raise TypeError("prod message") from e


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


def host_option_selected_map(host_select: ElementNode) -> dict[str, bool]:
    """Map option value string -> selected (last wins on duplicate values)."""

    out: dict[str, bool] = {}

    def walk_container(n: ElementNode) -> None:
        for ch in n.children:
            if not isinstance(ch, ElementNode):
                continue
            tl = ch.tag.lower()
            if tl == "option":
                v = ch.props.get("value")
                if v is None and ch.children and isinstance(ch.children[0], TextNode):
                    v = ch.children[0].text
                sv = "" if v is None else str(v)
                out[sv] = bool(ch.props.get("selected"))
            elif tl == "optgroup":
                walk_container(ch)

    walk_container(host_select)
    return out


def sync_host_select_controlled_selection(select_el: ElementNode) -> None:
    """After ``change``, re-apply ``<option selected>`` from the controlled ``value`` prop."""

    if "value" not in select_el.props:
        return

    def walk_collect(opts: list[ElementNode], n: ElementNode) -> None:
        for ch in n.children:
            if not isinstance(ch, ElementNode):
                continue
            tl = ch.tag.lower()
            if tl == "option":
                opts.append(ch)
            elif tl == "optgroup":
                walk_collect(opts, ch)

    opts: list[ElementNode] = []
    walk_collect(opts, select_el)
    opt_vals = []
    for o in opts:
        v = o.props.get("value")
        if v is None and o.children and isinstance(o.children[0], TextNode):
            v = o.children[0].text
        opt_vals.append("" if v is None else str(v))

    multiple = bool(select_el.props.get("multiple"))
    raw_val = select_el.props["value"]
    _validate_select_form_coercion(raw_val)
    coerced = _coerce_select_control_value(raw_val, multiple=multiple)
    if coerced is None:
        mask = [False] * len(opts)
    elif multiple and isinstance(coerced, set):
        mask = [v in coerced for v in opt_vals]
    else:
        assert isinstance(coerced, str)
        mask = [v == coerced for v in opt_vals]

    for o, sel in zip(opts, mask, strict=True):
        if sel:
            o.props["selected"] = True
        else:
            o.props.pop("selected", None)


def compute_option_selected_mask(
    *,
    raw: Mapping[str, Any],
    normalized_select_props: Mapping[str, Any],
    options: list[Element],
    host_select_prev: ElementNode | None = None,
) -> list[bool]:
    multiple = bool(normalized_select_props.get("multiple"))
    size_gt_1 = False
    sz = normalized_select_props.get("size")
    if sz is not None:
        try:
            size_gt_1 = int(sz) > 1
        except (TypeError, ValueError):
            size_gt_1 = False

    has_val = _prop_present(raw, "value")
    has_dv = _prop_present(raw, "defaultValue") or _prop_present(raw, "default_value")
    raw_val = raw["value"] if has_val else UNDEFINED_SENTINEL
    if _prop_present(raw, "defaultValue"):
        dv_raw = raw["defaultValue"]
    elif _prop_present(raw, "default_value"):
        dv_raw = raw["default_value"]
    else:
        dv_raw = UNDEFINED_SENTINEL

    opt_vals = [_option_element_value(o) for o in options]

    if has_val:
        v = None if raw_val is UNDEFINED_SENTINEL else raw_val
        if v is not None and _invalid_option_host_value(v) and not multiple:
            mask_id = []
            for o in options:
                if not _prop_present(o.props, "value"):
                    mask_id.append(False)
                    continue
                mask_id.append(o.props["value"] is v)
            if any(mask_id):
                return mask_id
            canon: str | None = None
            for o in options:
                if _prop_present(o.props, "value") and _invalid_option_host_value(o.props["value"]):
                    canon = _option_element_value(o)
                    break
            if canon is not None:
                return [x == canon for x in opt_vals]

        _validate_select_form_coercion(v)
        coerced = _coerce_select_control_value(v, multiple=multiple)
        if coerced is None:
            return [False] * len(options)
        if multiple and isinstance(coerced, set):
            return [v in coerced for v in opt_vals]
        assert isinstance(coerced, str)
        return [v == coerced for v in opt_vals]

    explicit = [bool(o.props.get("selected")) for o in options]
    if not has_val and any(explicit):
        return explicit

    if not has_val and host_select_prev is not None and host_select_prev.tag.lower() == "select":
        if has_dv and dv_raw is not UNDEFINED_SENTINEL:
            _validate_select_form_coercion(dv_raw)
        prev_map = host_option_selected_map(host_select_prev)
        return [prev_map.get(v, False) for v in opt_vals]

    if has_dv and dv_raw is not UNDEFINED_SENTINEL:
        _validate_select_form_coercion(dv_raw)
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
        if _truthy_disabled(o.props):
            continue
        if _prop_present(o.props, "value"):
            vvo = o.props["value"]
            if vvo is not None and _invalid_option_host_value(vvo):
                continue
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
    *,
    host_select_prev: ElementNode | None = None,
) -> tuple[Any, ...]:
    opts = iter_option_elements_in_select_children(children)
    multiple = bool(normalized_props.get("multiple"))
    if is_dev():
        _warn_select_dev(raw=raw_props, options=opts, multiple=multiple)
    mask = compute_option_selected_mask(
        raw=raw_props,
        normalized_select_props=normalized_props,
        options=opts,
        host_select_prev=host_select_prev,
    )
    return apply_select_binding_to_child_trees(children, mask)


def strip_select_internal_props(props: dict[str, Any], *, for_ssr: bool = False) -> None:
    for k in ("defaultValue", "default_value"):
        props.pop(k, None)
    if for_ssr:
        props.pop("value", None)
