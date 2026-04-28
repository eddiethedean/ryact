from __future__ import annotations

import warnings

from ryact import create_element
from ryact_dom.dom import Container, ElementNode
from ryact_dom.root import create_root
from ryact_dom.server import render_to_string


def test_delete_value_does_not_strip_my_icon_size_attribute() -> None:
    # Upstream: DOMPropertyOperations — "should not remove attributes for custom component tag"
    html = render_to_string(create_element("my-icon", {"size": "5px"}))
    assert 'size="5px"' in html

    container = Container()
    root = create_root(container)
    root.render(create_element("my-icon", {"size": "5px"}))
    host = container.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.props.get("size") == "5px"


def test_delete_value_does_not_strip_value_attr_when_input_becomes_uncontrolled() -> None:
    # Upstream: DOMPropertyOperations — "should not remove attributes for special properties"
    def on_change() -> None:
        return

    c = Container()
    root = create_root(c)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        root.render(
            create_element("input", {"type": "text", "value": "foo", "onChange": on_change}),
        )
        root.render(create_element("input", {"type": "text", "onChange": on_change}))
        h = c.root.children[0]
        assert isinstance(h, ElementNode)
        assert h.props.get("value") == "foo"
    assert w and "controlled" in str(w[0].message) and "uncontrolled" in str(w[0].message)
