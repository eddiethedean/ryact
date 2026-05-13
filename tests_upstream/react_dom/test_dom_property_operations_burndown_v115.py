# Translated: DOMPropertyOperations-test.js — custom element ``deleteValueForProperty`` defaults (v115)
from __future__ import annotations

from ryact import create_element
from ryact_dom.dom import Container, ElementNode
from ryact_dom.root import create_root


def test_custom_element_removed_props_restore_registered_defaults() -> None:
    """Upstream: ``object`` / ``string`` use ``in`` + setters; removals map to ``null`` / ``\"\"``."""

    obj = 12345
    c = Container()
    root = create_root(c)
    root.render(create_element("my-custom-element", {"raw": 2, "object": obj, "string": "hi"}))
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.props["raw"] == 2
    assert host.props["object"] == obj
    assert host.props["string"] == "hi"

    host.register_custom_property_removed_value("object", None)
    host.register_custom_property_removed_value("string", "")

    root.render(create_element("my-custom-element", {}))
    host2 = c.root.children[0]
    assert isinstance(host2, ElementNode)
    assert "raw" not in host2.props
    assert host2.props.get("object") is None
    assert host2.props.get("string") == ""
