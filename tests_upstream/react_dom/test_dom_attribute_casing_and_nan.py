from __future__ import annotations

import math
import warnings

from ryact import create_element
from ryact.dev import is_dev
from ryact_dom.dom import Container, ElementNode
from ryact_dom.root import create_root
from ryact_dom.server import render_to_string


def test_bad_casing_known_dom_prop_normalized_to_canonical() -> None:
    # Upstream: ReactDOMComponent-test.js — "warns on bad casing of known HTML attributes"
    html = render_to_string(create_element("div", {"SiZe": "30"}))
    assert 'size="30"' in html.lower()

    container = Container()
    root = create_root(container)
    root.render(create_element("div", {"SiZe": "30"}))
    host = container.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.props.get("size") == "30"
    assert "SiZe" not in host.props

    if is_dev():
        with warnings.catch_warnings(record=True) as rec:
            warnings.simplefilter("always")
            render_to_string(create_element("div", {"SiZe": "7"}))
        assert any("SiZe" in str(w.message) for w in rec)


def test_nan_custom_attribute_stringified_with_dev_warning() -> None:
    # Upstream: ReactDOMComponent-test.js — "warns on NaN attributes"
    html = render_to_string(create_element("div", {"whatever": float("nan")}))
    assert "nan" in html.lower()

    container = Container()
    root = create_root(container)
    root.render(create_element("div", {"whatever": float("nan")}))
    host = container.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.props.get("whatever") == "NaN"

    if is_dev():
        with warnings.catch_warnings(record=True) as rec:
            warnings.simplefilter("always")
            render_to_string(create_element("div", {"whatever": math.nan}))
        assert any("nan" in str(w.message).lower() for w in rec)
