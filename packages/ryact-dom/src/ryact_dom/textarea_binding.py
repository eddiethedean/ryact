# ``<textarea>`` value / ``defaultValue`` binding (ReactDOMTextarea parity subset).
from __future__ import annotations

import warnings
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from ryact.dev import is_dev
from ryact.element import UNDEFINED

from .dom import ElementNode, TextNode

_TEXTAREA_CHILDREN_WARN = (
    "Use the `defaultValue` or `value` props instead of setting children on <textarea>.\n"
    "    in textarea"
)


def _prop_present(raw: Mapping[str, Any], key: str) -> bool:
    if key not in raw:
        return False
    return raw[key] is not UNDEFINED


def _invalid_textarea_host_value(v: Any) -> bool:
    return (callable(v) and not isinstance(v, type)) or type(v).__name__ == "Symbol"


def _walk_text_parts(children: object) -> list[str]:
    if children is None:
        return []
    if _invalid_textarea_host_value(children):
        return []
    if isinstance(children, (str, int, float)):
        return [str(children)]
    if isinstance(children, Sequence) and not isinstance(children, (str, bytes)):
        out: list[str] = []
        for c in children:
            out.extend(_walk_text_parts(c))
        return out
    if isinstance(children, Mapping):
        return []
    return [str(children)]


def _textarea_children_present(children: object) -> bool:
    if children is None:
        return False
    if isinstance(children, (str, int, float)) or _invalid_textarea_host_value(children):
        return True
    if isinstance(children, Sequence) and not isinstance(children, (str, bytes)):
        return any(_textarea_children_present(c) for c in children)
    return True


def warn_textarea_children_dev(children: object) -> None:
    if not is_dev():
        return
    if not _textarea_children_present(children):
        return
    warnings.warn(_TEXTAREA_CHILDREN_WARN, UserWarning, stacklevel=5)


def _textarea_stringify(
    v: Any,
    *,
    prop: str,
    coerce_temporal: bool = True,
) -> str:
    if _invalid_textarea_host_value(v):
        if is_dev():
            warnings.warn(
                f"Invalid value for prop `{prop}` on <textarea> tag. "
                "Either remove it from the element, or pass a string or number value to "
                "keep it in the DOM. For details, see https://react.dev/link/attribute-behavior \n"
                "    in textarea",
                UserWarning,
                stacklevel=5,
            )
        return ""
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float) and v == v and v == int(v):
        return str(int(v))
    if not isinstance(v, (str, int, float, bool)) and hasattr(v, "valueOf"):
        try:
            v.valueOf()
        except TypeError as e:
            if is_dev():
                warnings.warn(
                    "Form field values (value, checked, defaultValue, or defaultChecked props) must be "
                    f"strings, not {type(v).__name__}. This value must be coerced to a string before "
                    "using it here.\n"
                    "    in textarea",
                    UserWarning,
                    stacklevel=5,
                )
            raise TypeError(e.args[0] if e.args else "coercion failed") from e
    try:
        return str(v)
    except TypeError as e:
        if is_dev():
            warnings.warn(
                "Form field values (value, checked, defaultValue, or defaultChecked props) must be "
                f"strings, not {type(v).__name__}. This value must be coerced to a string before "
                "using it here.\n"
                "    in textarea",
                UserWarning,
                stacklevel=5,
            )
        if coerce_temporal:
            raise TypeError(e.args[0] if e.args else "coercion failed") from e
        raise


def _controlled_from_raw(raw: Mapping[str, Any]) -> bool:
    if not _prop_present(raw, "value"):
        return False
    return raw["value"] is not None


def _resolve_text_from_raw(
    raw: Mapping[str, Any],
    *,
    children: object,
    host_prev: ElementNode | None,
) -> tuple[str, bool, str, bool]:
    """
    Returns ``(text, controlled, host_default_value, omit_initial_empty)``.
    """

    controlled = _controlled_from_raw(raw)
    host_dv = ""
    omit_initial_empty = False

    if controlled:
        text = _textarea_stringify(raw["value"], prop="value")
        if text == "" and _read_only_truthy(raw):
            omit_initial_empty = host_prev is None
        return text, True, host_dv, omit_initial_empty

    if _prop_present(raw, "defaultValue"):
        dv = raw["defaultValue"]
        if dv is None:
            host_dv = ""
        elif _invalid_textarea_host_value(dv):
            if host_prev is not None:
                return (
                    _textarea_text_from_host(host_prev),
                    False,
                    _textarea_host_default_value_from_host(host_prev),
                    False,
                )
            return "", False, "", False
        else:
            host_dv = _textarea_stringify(dv, prop="defaultValue", coerce_temporal=False)
            text = _textarea_text_from_host(host_prev) if host_prev is not None else host_dv
            return text, False, host_dv, False

    if _textarea_children_present(children):
        warn_textarea_children_dev(children)
    parts = _walk_text_parts(children)
    if parts or _textarea_children_present(children):
        text = "".join(parts)
        if host_prev is not None:
            text = _textarea_text_from_host(host_prev)
        host_dv = text if host_prev is None else _textarea_host_default_value_from_host(host_prev)
        return text, False, host_dv if host_prev is None else host_dv, False

    if host_prev is not None:
        return (
            _textarea_text_from_host(host_prev),
            False,
            "",
            False,
        )
    return "", False, "", False


def _read_only_truthy(raw: Mapping[str, Any]) -> bool:
    ro = raw.get("readOnly")
    if ro is None:
        ro = raw.get("read_only")
    return ro is True or ro == ""


def _textarea_text_from_host(host: ElementNode) -> str:
    if host.children and isinstance(host.children[0], TextNode):
        return host.children[0].text
    return ""


def _textarea_host_default_value_from_host(host: ElementNode) -> str:
    return str(getattr(host, "_textarea_host_default_value", ""))


@dataclass(frozen=True)
class TextareaBindingResult:
    children: tuple[Any, ...]
    controlled: bool
    host_default_value: str
    omit_initial_empty: bool


def process_textarea_element_children(
    raw: Mapping[str, Any],
    props: dict[str, Any],
    children: object,
    *,
    host_prev: ElementNode | None = None,
) -> TextareaBindingResult:
    text, controlled, host_dv, omit_empty = _resolve_text_from_raw(
        raw, children=children, host_prev=host_prev
    )
    if controlled and _prop_present(raw, "value") and raw["value"] is None and is_dev():
        warnings.warn(
            "`value` prop on `textarea` should not be null. "
            "Consider using an empty string to clear the component or `undefined` "
            "for uncontrolled components.\n"
            "    in textarea",
            UserWarning,
            stacklevel=5,
        )
    out_children: tuple[Any, ...]
    if omit_empty and text == "" or text == "" and not controlled and not children and host_prev is None:
        out_children = ()
    else:
        out_children = (text,)
    return TextareaBindingResult(
        children=out_children,
        controlled=controlled,
        host_default_value=host_dv,
        omit_initial_empty=omit_empty,
    )


def strip_textarea_internal_props(props: dict[str, Any], *, for_ssr: bool = False) -> None:
    for k in ("value", "defaultValue", "default_value"):
        props.pop(k, None)
    if for_ssr:
        return
