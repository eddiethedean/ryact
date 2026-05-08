# Translated: ReactDOMComponent-test.js — Object stringification + whitespace (burndown v93)
from __future__ import annotations

from ryact import create_element
from ryact_dom.dom import Container
from ryact_dom.root import create_root
from ryact_dom.server import render_to_string

_WS_HTML = "\n  \t  <span>  \n  testContent  \t  </span>  \n  \t"
_WS_HTML2 = "\n  \t  <div>  \n  testContent2  \t  </div>  \n  \t"


def test_renders_innerhtml_and_preserves_whitespace_ssr() -> None:
    out = render_to_string(create_element("div", {"dangerouslySetInnerHTML": {"__html": _WS_HTML}}))
    start = out.index(">") + 1
    end = out.rindex("</")
    assert out[start:end] == _WS_HTML


def test_renders_innerhtml_and_preserves_whitespace_host() -> None:
    c = Container()
    root = create_root(c)
    root.render(create_element("div", {"dangerouslySetInnerHTML": {"__html": _WS_HTML}}))
    div = c.root.children[0]
    assert div.innerHTML == _WS_HTML


def test_updates_innerhtml_and_preserves_whitespace_host() -> None:
    c = Container()
    root = create_root(c)
    root.render(create_element("div", {"dangerouslySetInnerHTML": {"__html": _WS_HTML}}))
    root.render(create_element("div", {"dangerouslySetInnerHTML": {"__html": _WS_HTML2}}))
    div = c.root.children[0]
    assert div.innerHTML == _WS_HTML2


class _HelloObj:
    def __str__(self) -> str:
        return "hello"


def test_allows_objects_on_known_accept_charset_property() -> None:
    html = render_to_string(create_element("div", {"acceptCharset": {}}))
    assert 'accept-charset="[object Object]"' in html


def test_passes_objects_as_attributes_if_they_define_to_string() -> None:
    obj = _HelloObj()
    html_img = render_to_string(create_element("img", {"src": obj}))
    assert 'src="hello"' in html_img

    html_svg = render_to_string(create_element("svg", {"arabicForm": obj}))
    assert 'arabic-form="hello"' in html_svg

    html_div = render_to_string(create_element("div", {"unknown": obj}))
    assert 'unknown="hello"' in html_div


def test_passes_objects_on_known_svg_attributes_if_no_to_string() -> None:
    html = render_to_string(create_element("svg", {"arabicForm": {}}))
    assert 'arabic-form="[object Object]"' in html


def test_passes_objects_on_custom_attributes_if_no_to_string() -> None:
    html = render_to_string(create_element("div", {"unknown": {}}))
    assert 'unknown="[object Object]"' in html


class _ParentImg:
    def __str__(self) -> str:
        return "hello.jpg"


class _ChildImg(_ParentImg):
    pass


def test_allows_objects_that_inherit_custom_to_string_for_src() -> None:
    html = render_to_string(create_element("img", {"src": _ChildImg()}))
    assert 'src="hello.jpg"' in html


class _Ajaxify:
    def __str__(self) -> str:
        return "ajaxy"


def test_assigns_ajaxify_internal_attribute_via_to_string() -> None:
    html = render_to_string(create_element("div", {"ajaxify": _Ajaxify()}))
    assert 'ajaxify="ajaxy"' in html
