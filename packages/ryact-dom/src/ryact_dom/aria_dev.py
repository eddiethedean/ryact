"""DEV-only ARIA attribute validation (parity target: React ``ReactDOMInvalidARIAHook``)."""

from __future__ import annotations

import re
import warnings
from collections.abc import Mapping
from typing import Any

from ryact.dev import is_dev

# Mirrors ``packages/react-dom-bindings/src/shared/validAriaProperties.js`` (main branch).
_VALID_ARIA_HTML_NAMES: frozenset[str] = frozenset(
    {
        "aria-current",
        "aria-description",
        "aria-details",
        "aria-disabled",
        "aria-hidden",
        "aria-invalid",
        "aria-keyshortcuts",
        "aria-label",
        "aria-roledescription",
        "aria-autocomplete",
        "aria-checked",
        "aria-expanded",
        "aria-haspopup",
        "aria-level",
        "aria-modal",
        "aria-multiline",
        "aria-multiselectable",
        "aria-orientation",
        "aria-placeholder",
        "aria-pressed",
        "aria-readonly",
        "aria-required",
        "aria-selected",
        "aria-sort",
        "aria-valuemax",
        "aria-valuemin",
        "aria-valuenow",
        "aria-valuetext",
        "aria-atomic",
        "aria-busy",
        "aria-live",
        "aria-relevant",
        "aria-dropeffect",
        "aria-grabbed",
        "aria-activedescendant",
        "aria-colcount",
        "aria-colindex",
        "aria-colspan",
        "aria-controls",
        "aria-describedby",
        "aria-errormessage",
        "aria-flowto",
        "aria-labelledby",
        "aria-owns",
        "aria-posinset",
        "aria-rowcount",
        "aria-rowindex",
        "aria-rowspan",
        "aria-setsize",
        "aria-braillelabel",
        "aria-brailleroledescription",
        "aria-colindextext",
        "aria-rowindextext",
    }
)

_ARIA_RECOGNIZED_CAMEL_TO_CANONICAL: dict[str, str] = {
    "ariaHasPopup": "aria-haspopup",
}


def warn_invalid_aria_props_for_host_dev(props: Mapping[str, Any], *, tag: str | None) -> None:
    if not is_dev():
        return
    where = tag or "element"
    invalid_hyphen: list[str] = []
    for k in props:
        if k == "children":
            continue
        if k.startswith("aria-"):
            canon = next((n for n in _VALID_ARIA_HTML_NAMES if n.casefold() == k.casefold()), None)
            if canon is None:
                invalid_hyphen.append(k)
            elif k != canon:
                warnings.warn(
                    f"Unknown ARIA attribute `{k}`. Did you mean `{canon}`?\n    in {where}",
                    UserWarning,
                    stacklevel=5,
                )
            continue
        if k.startswith("aria_"):
            hyphen = "aria-" + k[5:].replace("_", "-").lower()
            if hyphen in _VALID_ARIA_HTML_NAMES:
                continue
            invalid_hyphen.append(k)
            continue
        if re.match(r"^aria[A-Z]", k):
            if k in _ARIA_RECOGNIZED_CAMEL_TO_CANONICAL:
                canon = _ARIA_RECOGNIZED_CAMEL_TO_CANONICAL[k]
                warnings.warn(
                    f"Invalid ARIA attribute `{k}`. Did you mean `{canon}`?\n    in {where}",
                    UserWarning,
                    stacklevel=5,
                )
            else:
                warnings.warn(
                    (
                        f"Invalid ARIA attribute `{k}`. ARIA attributes follow the pattern aria-* "
                        f"and must be lowercase.\n    in {where}"
                    ),
                    UserWarning,
                    stacklevel=5,
                )
    if invalid_hyphen:
        if len(invalid_hyphen) == 1:
            a = invalid_hyphen[0]
            warnings.warn(
                (
                    f"Invalid aria prop `{a}` on <{where}> tag. For details, see "
                    "https://react.dev/link/invalid-aria-props\n"
                    f"    in {where}"
                ),
                UserWarning,
                stacklevel=5,
            )
        else:
            names = ", ".join(f"`{a}`" for a in sorted(invalid_hyphen))
            warnings.warn(
                (
                    f"Invalid aria props {names} on <{where}> tag. For details, see "
                    "https://react.dev/link/invalid-aria-props\n"
                    f"    in {where}"
                ),
                UserWarning,
                stacklevel=5,
            )
