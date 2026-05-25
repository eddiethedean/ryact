from __future__ import annotations

HTML_NAMESPACE = "http://www.w3.org/1999/xhtml"
SVG_NAMESPACE = "http://www.w3.org/2000/svg"
XLINK_NAMESPACE = "http://www.w3.org/1999/xlink"

_SVG_INTRINSIC_TAGS: frozenset[str] = frozenset(
    {
        "svg",
        "g",
        "circle",
        "path",
        "rect",
        "line",
        "polyline",
        "polygon",
        "ellipse",
        "image",
        "text",
        "tspan",
        "defs",
        "clippath",
        "mask",
        "pattern",
        "lineargradient",
        "radialgradient",
        "stop",
        "use",
        "symbol",
        "foreignobject",
    }
)


def is_svg_host_tag(tag: str) -> bool:
    return tag.lower() in _SVG_INTRINSIC_TAGS


def namespace_for_host_child(*, parent_tag: str | None, parent_namespace: str | None, tag: str) -> str:
    """Resolve namespaceURI for a host child (ReactDOMSVG parity subset)."""

    tl = tag.lower()
    if parent_namespace == SVG_NAMESPACE:
        if parent_tag is not None and parent_tag.lower() == "foreignobject":
            return HTML_NAMESPACE
        if is_svg_host_tag(tl):
            return SVG_NAMESPACE
        return HTML_NAMESPACE
    if tl == "svg" or (parent_tag is not None and parent_tag.lower() == "svg"):
        return SVG_NAMESPACE
    if is_svg_host_tag(tl) and parent_namespace == SVG_NAMESPACE:
        return SVG_NAMESPACE
    return HTML_NAMESPACE


def host_tag_name_for_namespace(*, tag: str, namespace_uri: str) -> str:
    if namespace_uri == SVG_NAMESPACE:
        return tag if tag != tag.upper() else tag.lower()
    return tag.upper()


def serialize_xlink_href_attr(props: dict[str, object]) -> str | None:
    for key in ("xlinkHref", "xlink:href"):
        v = props.get(key)
        if v is not None and not callable(v):
            return f' xlink:href="{v}"'
    return None
