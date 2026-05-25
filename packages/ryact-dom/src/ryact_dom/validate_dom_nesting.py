# DEV-only HTML nesting validation (React ``validateDOMNesting`` / ``validateTextNesting`` parity subset).
from __future__ import annotations

import warnings
from dataclasses import dataclass

from typing import Any

from ryact.dev import is_dev

from .dom_dev_warnings import dev_in_host_line, react_dev_in_suffix, react_dev_owner_stack_suffix

# https://html.spec.whatwg.org/multipage/syntax.html#special
_SPECIAL_TAGS: frozenset[str] = frozenset(
    {
        "address",
        "applet",
        "area",
        "article",
        "aside",
        "base",
        "basefont",
        "bgsound",
        "blockquote",
        "body",
        "br",
        "button",
        "caption",
        "center",
        "col",
        "colgroup",
        "dd",
        "details",
        "dir",
        "div",
        "dl",
        "dt",
        "embed",
        "fieldset",
        "figcaption",
        "figure",
        "footer",
        "form",
        "frame",
        "frameset",
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
        "iframe",
        "img",
        "input",
        "isindex",
        "li",
        "link",
        "listing",
        "main",
        "marquee",
        "menu",
        "menuitem",
        "meta",
        "nav",
        "noembed",
        "noframes",
        "noscript",
        "object",
        "ol",
        "p",
        "param",
        "plaintext",
        "pre",
        "script",
        "section",
        "select",
        "source",
        "style",
        "summary",
        "table",
        "tbody",
        "td",
        "template",
        "textarea",
        "tfoot",
        "th",
        "thead",
        "title",
        "tr",
        "track",
        "ul",
        "wbr",
        "xmp",
    }
)

_IN_SCOPE_TAGS: frozenset[str] = frozenset(
    {
        "applet",
        "caption",
        "html",
        "table",
        "td",
        "th",
        "marquee",
        "object",
        "template",
        "foreignobject",
        "desc",
        "title",
    }
)

_BUTTON_SCOPE_TAGS: frozenset[str] = _IN_SCOPE_TAGS | {"button"}

_IMPLIED_END_TAGS: frozenset[str] = frozenset(
    {"dd", "dt", "li", "option", "optgroup", "p", "rp", "rt"}
)

_did_warn: set[str] = set()


def reset_validate_dom_nesting_dev_state() -> None:
    _did_warn.clear()


@dataclass
class _Info:
    tag: str


@dataclass
class AncestorInfoDev:
    current: _Info | None = None
    form_tag: _Info | None = None
    a_tag_in_scope: _Info | None = None
    button_tag_in_scope: _Info | None = None
    nobr_tag_in_scope: _Info | None = None
    p_tag_in_button_scope: _Info | None = None
    list_item_tag_autoclosing: _Info | None = None
    dl_item_tag_autoclosing: _Info | None = None
    container_tag_in_scope: _Info | None = None
    implicit_root_scope: bool = False


def _ancestor_info_copy(old: AncestorInfoDev | None) -> AncestorInfoDev:
    if old is None:
        return AncestorInfoDev()
    return AncestorInfoDev(
        current=old.current,
        form_tag=old.form_tag,
        a_tag_in_scope=old.a_tag_in_scope,
        button_tag_in_scope=old.button_tag_in_scope,
        nobr_tag_in_scope=old.nobr_tag_in_scope,
        p_tag_in_button_scope=old.p_tag_in_button_scope,
        list_item_tag_autoclosing=old.list_item_tag_autoclosing,
        dl_item_tag_autoclosing=old.dl_item_tag_autoclosing,
        container_tag_in_scope=old.container_tag_in_scope,
        implicit_root_scope=old.implicit_root_scope,
    )


def updated_ancestor_info_dev(old_info: AncestorInfoDev | None, tag: str) -> AncestorInfoDev:
    """Mirror ``updatedAncestorInfoDev`` from React's ``validateDOMNesting``."""

    ancestor_info = _ancestor_info_copy(old_info)
    info = _Info(tag=tag)

    if tag in _IN_SCOPE_TAGS:
        ancestor_info.a_tag_in_scope = None
        ancestor_info.button_tag_in_scope = None
        ancestor_info.nobr_tag_in_scope = None
    if tag in _BUTTON_SCOPE_TAGS:
        ancestor_info.p_tag_in_button_scope = None

    if tag in _SPECIAL_TAGS and tag not in ("address", "div", "p"):
        ancestor_info.list_item_tag_autoclosing = None
        ancestor_info.dl_item_tag_autoclosing = None

    ancestor_info.current = info

    if tag == "form":
        ancestor_info.form_tag = info
    if tag == "a":
        ancestor_info.a_tag_in_scope = info
    if tag == "button":
        ancestor_info.button_tag_in_scope = info
    if tag == "nobr":
        ancestor_info.nobr_tag_in_scope = info
    if tag == "p":
        ancestor_info.p_tag_in_button_scope = info
    if tag == "li":
        ancestor_info.list_item_tag_autoclosing = info
    if tag in ("dd", "dt"):
        ancestor_info.dl_item_tag_autoclosing = info

    if tag in ("#document", "html"):
        ancestor_info.container_tag_in_scope = None
    elif ancestor_info.container_tag_in_scope is None:
        ancestor_info.container_tag_in_scope = info

    if old_info is None and tag in ("#document", "html", "body"):
        ancestor_info.implicit_root_scope = True
    elif ancestor_info.implicit_root_scope is True:
        ancestor_info.implicit_root_scope = False

    return ancestor_info


def initial_ancestor_info_dev(container: Any | None) -> AncestorInfoDev:
    if container is not None and getattr(container, "dom_nesting_mount_tag", None):
        return updated_ancestor_info_dev(None, str(container.dom_nesting_mount_tag).lower())
    return updated_ancestor_info_dev(None, "#document")


def _is_tag_valid_with_parent(
    tag: str, parent_tag: str | None, implicit_root_scope: bool
) -> bool:
    if parent_tag == "select":
        return tag in {"hr", "option", "optgroup", "script", "template", "#text"}
    if parent_tag == "optgroup":
        return tag in {"option", "#text"}
    if parent_tag == "option":
        return tag == "#text"
    if parent_tag == "tr":
        return tag in {"th", "td", "style", "script", "template"}
    if parent_tag in ("tbody", "thead", "tfoot"):
        return tag in {"tr", "style", "script", "template"}
    if parent_tag == "colgroup":
        return tag in {"col", "template"}
    if parent_tag == "table":
        return tag in {
            "caption",
            "colgroup",
            "tbody",
            "tfoot",
            "thead",
            "style",
            "script",
            "template",
        }
    if parent_tag == "head":
        return tag in {
            "base",
            "basefont",
            "bgsound",
            "link",
            "meta",
            "title",
            "noscript",
            "noframes",
            "style",
            "script",
            "template",
        }
    if parent_tag == "html":
        if not implicit_root_scope:
            return tag in {"head", "body", "frameset"}
    if parent_tag == "frameset":
        return tag == "frame"
    if parent_tag == "#document":
        if not implicit_root_scope:
            return tag == "html"

    if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
        return parent_tag not in {"h1", "h2", "h3", "h4", "h5", "h6"}
    if tag in {"rp", "rt"}:
        return parent_tag not in _IMPLIED_END_TAGS
    if tag in {
        "caption",
        "col",
        "colgroup",
        "frameset",
        "frame",
        "tbody",
        "td",
        "tfoot",
        "th",
        "thead",
        "tr",
    }:
        return parent_tag is None
    if tag == "head":
        return implicit_root_scope or parent_tag is None
    if tag == "html":
        return (implicit_root_scope and parent_tag == "#document") or parent_tag is None
    if tag == "body":
        return (
            implicit_root_scope and parent_tag in ("#document", "html")
        ) or parent_tag is None

    return True


def _find_invalid_ancestor_for_tag(tag: str, ancestor_info: AncestorInfoDev) -> _Info | None:
    if tag in {
        "address",
        "article",
        "aside",
        "blockquote",
        "center",
        "details",
        "dialog",
        "dir",
        "div",
        "dl",
        "fieldset",
        "figcaption",
        "figure",
        "footer",
        "header",
        "hgroup",
        "main",
        "menu",
        "nav",
        "ol",
        "p",
        "section",
        "summary",
        "ul",
        "pre",
        "listing",
        "table",
        "hr",
        "xmp",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
    }:
        return ancestor_info.p_tag_in_button_scope

    if tag == "form":
        return ancestor_info.form_tag or ancestor_info.p_tag_in_button_scope

    if tag == "li":
        return ancestor_info.list_item_tag_autoclosing

    if tag in ("dd", "dt"):
        return ancestor_info.dl_item_tag_autoclosing

    if tag == "button":
        return ancestor_info.button_tag_in_scope

    if tag == "a":
        return ancestor_info.a_tag_in_scope

    if tag == "nobr":
        return ancestor_info.nobr_tag_in_scope

    return None


def validate_dom_nesting_host_child_dev(
    *,
    child_tag: str,
    ancestor_info: AncestorInfoDev,
    component_stack: str,
) -> None:
    if not is_dev():
        return

    child_tag_l = child_tag.lower()
    parent_info = ancestor_info.current
    parent_tag = parent_info.tag if parent_info else None

    invalid_parent_info = (
        None
        if _is_tag_valid_with_parent(child_tag_l, parent_tag, ancestor_info.implicit_root_scope)
        else parent_info
    )
    invalid_ancestor = (
        None
        if invalid_parent_info is not None
        else _find_invalid_ancestor_for_tag(child_tag_l, ancestor_info)
    )
    invalid = invalid_parent_info or invalid_ancestor
    if invalid is None:
        return

    ancestor_tag = invalid.tag
    warn_key = f"{invalid_parent_info is not None}|{child_tag_l}|{ancestor_tag}"
    if warn_key in _did_warn:
        return
    _did_warn.add(warn_key)

    tag_display = f"<{child_tag_l}>"
    suffix = react_dev_in_suffix(host_tag=child_tag_l, owner_stack=component_stack)
    ancestor_description = f"\n{suffix}" if suffix else ""

    if invalid_parent_info is not None:
        extra = ""
        if ancestor_tag == "table" and child_tag_l == "tr":
            extra = (
                " Add a <tbody>, <thead> or <tfoot> to your code to match the DOM tree generated "
                "by the browser."
            )
        msg = (
            f"In HTML, {tag_display} cannot be a child of <{ancestor_tag}>.{extra}\n"
            f"This will cause a hydration error.{ancestor_description}"
        )
        warnings.warn(msg, UserWarning, stacklevel=3)
        if ancestor_tag == "table" and child_tag_l == "tr":
            nk = f"nested|{warn_key}"
            if nk not in _did_warn:
                _did_warn.add(nk)
                trace_parts = [dev_in_host_line(ancestor_tag)]
                owner = react_dev_owner_stack_suffix(component_stack)
                if owner:
                    trace_parts.append(owner)
                trace_desc = "\n" + "\n".join(trace_parts)
                msg2 = (
                    f"<{ancestor_tag}> cannot contain a nested {tag_display}.\n"
                    f"See this log for the ancestor stack trace.{trace_desc}"
                )
                warnings.warn(msg2, UserWarning, stacklevel=3)
    else:
        msg = (
            f"In HTML, {tag_display} cannot be a descendant of <{ancestor_tag}>.\n"
            f"This will cause a hydration error.{ancestor_description}"
        )
        warnings.warn(msg, UserWarning, stacklevel=3)


def validate_text_nesting_dev(*, text: str, ancestor_info: AncestorInfoDev, component_stack: str) -> None:
    if not is_dev():
        return

    if ancestor_info.current is None:
        return
    parent_tag = ancestor_info.current.tag
    if ancestor_info.implicit_root_scope or _is_tag_valid_with_parent("#text", parent_tag, False):
        return

    warn_key = f"#text|{parent_tag}"
    if warn_key in _did_warn:
        return
    _did_warn.add(warn_key)

    suffix = react_dev_in_suffix(host_tag=parent_tag, owner_stack=component_stack)
    ancestor_description = f"\n{suffix}" if suffix else ""

    if text.strip():
        msg = (
            f"In HTML, text nodes cannot be a child of <{parent_tag}>.\n"
            f"This will cause a hydration error.{ancestor_description}"
        )
    else:
        msg = (
            f"In HTML, whitespace text nodes cannot be a child of <{parent_tag}>. "
            "Make sure you don't have any extra whitespace between tags on "
            "each line of your source code.\n"
            f"This will cause a hydration error.{ancestor_description}"
        )
    warnings.warn(msg, UserWarning, stacklevel=3)
