from __future__ import annotations

import warnings
from typing import Any

from ryact.dev import is_dev

from .html_props import _HYPHENATED_BUILTIN_TAGS

# Subset of WHATWG / browser intrinsic tag names (lowercase). Used only for DEV unrecognized-tag nudges.
_HTML_INTRINSIC_TAGS: frozenset[str] = frozenset(
    {
        "a",
        "abbr",
        "address",
        "area",
        "article",
        "aside",
        "audio",
        "b",
        "base",
        "bdi",
        "bdo",
        "blockquote",
        "body",
        "br",
        "button",
        "canvas",
        "caption",
        "cite",
        "code",
        "col",
        "colgroup",
        "data",
        "datalist",
        "dd",
        "del",
        "details",
        "dfn",
        "dialog",
        "div",
        "dl",
        "dt",
        "em",
        "embed",
        "fieldset",
        "figcaption",
        "figure",
        "footer",
        "form",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "head",
        "header",
        "hgroup",
        "hr",
        "html",
        "i",
        "iframe",
        "img",
        "input",
        "ins",
        "kbd",
        "label",
        "legend",
        "li",
        "link",
        "main",
        "map",
        "mark",
        "menu",
        "menuitem",
        "meta",
        "meter",
        "nav",
        "noscript",
        "object",
        "ol",
        "optgroup",
        "option",
        "output",
        "p",
        "picture",
        "pre",
        "progress",
        "q",
        "rp",
        "rt",
        "ruby",
        "s",
        "samp",
        "script",
        "section",
        "select",
        "slot",
        "small",
        "source",
        "span",
        "strong",
        "style",
        "sub",
        "summary",
        "sup",
        "svg",
        "table",
        "tbody",
        "td",
        "template",
        "textarea",
        "tfoot",
        "th",
        "thead",
        "time",
        "title",
        "tr",
        "track",
        "u",
        "ul",
        "var",
        "video",
        "wbr",
    }
)

_SVG_CHILD_TAGS: frozenset[str] = frozenset(
    {
        "a",
        "animate",
        "animatemotion",
        "animatetransform",
        "circle",
        "clippath",
        "defs",
        "desc",
        "ellipse",
        "feblend",
        "fecolormatrix",
        "fecomponenttransfer",
        "fecomposite",
        "feconvolvematrix",
        "fediffuselighting",
        "fedisplacementmap",
        "fedistantlight",
        "fedropshadow",
        "feflood",
        "fefunca",
        "fefuncb",
        "fefuncg",
        "fefuncr",
        "fegaussianblur",
        "feimage",
        "femerge",
        "femergenode",
        "femorphology",
        "feoffset",
        "fepointlight",
        "fespecularlighting",
        "fespotlight",
        "fetile",
        "feturbulence",
        "filter",
        "foreignobject",
        "g",
        "image",
        "line",
        "lineargradient",
        "marker",
        "mask",
        "metadata",
        "mpath",
        "path",
        "pattern",
        "polygon",
        "polyline",
        "radialgradient",
        "rect",
        "stop",
        "svg",
        "switch",
        "symbol",
        "text",
        "textpath",
        "title",
        "tspan",
        "use",
        "view",
    }
)

_UNRECOGNIZED_TAG_WARNED: set[str] = set()


def reset_intrinsic_tag_dev_warning_state() -> None:
    """Clear DEV unrecognized-tag dedupe state (translated DOM tests)."""

    _UNRECOGNIZED_TAG_WARNED.clear()


def warn_unrecognized_host_tag_dev(tag: str, parent_host_tag: str | None) -> None:
    """DEV-only: intrinsic tag is not a known HTML/SVG/MathML integration name (ReactDOM mountComponent subset)."""

    if not is_dev() or not tag:
        return
    tl = tag.lower()
    p = parent_host_tag.lower() if parent_host_tag else None
    if p == "svg":
        if tl in _SVG_CHILD_TAGS:
            return
    elif p == "math":
        return
    elif tl in _HTML_INTRINSIC_TAGS:
        return
    if "-" in tag:
        if tl in _HYPHENATED_BUILTIN_TAGS:
            return
        return
    key = tl
    if key in _UNRECOGNIZED_TAG_WARNED:
        return
    _UNRECOGNIZED_TAG_WARNED.add(key)
    warnings.warn(
        f"The tag <{tl}> is unrecognized in this browser. "
        "If you meant to render a React component, start its name with an uppercase letter.\n"
        f"    in {tl}",
        UserWarning,
        stacklevel=4,
    )


def format_dangerously_inner_html_value_dev(v: Any) -> str:
    """Best-effort match for React's ``toString``-based ``dangerouslySetInnerHTML`` coercion."""

    return str(v)
