from __future__ import annotations

from ryact import create_element
from ryact_dom.dom import Container
from ryact_dom.root import create_root
from ryact_testkit import WarningCapture


def test_warns_for_duplicated_array_keys_with_component_stack_info() -> None:
    # Upstream: ReactChildReconciler-test.js
    # "warns for duplicated array keys with component stack info"
    container = Container()
    root = create_root(container)

    def App() -> object:
        # Duplicate keys: "a"
        return create_element(
            "ul",
            None,
            create_element("li", {"key": "a"}),
            create_element("li", {"key": "a"}),
        )

    with WarningCapture() as wc:
        root.render(create_element(App))

    wc.assert_any("Encountered two children with the same key")
    wc.assert_any("Component stack:")
    wc.assert_any("in App")


def test_warns_for_duplicated_iterable_keys_with_component_stack_info() -> None:
    # Upstream: ReactChildReconciler-test.js
    # "warns for duplicated iterable keys with component stack info"
    container = Container()
    root = create_root(container)

    def App() -> object:
        # Iterable children (tuple), duplicate keys: "b"
        kids = (create_element("li", {"key": "b"}), create_element("li", {"key": "b"}))
        return create_element("ul", {"children": kids})

    with WarningCapture() as wc:
        root.render(create_element(App))

    wc.assert_any("Encountered two children with the same key")
    wc.assert_any("Component stack:")
    wc.assert_any("in App")


def test_warns_for_duplicated_array_keys_with_component_stack_info_multichild() -> None:
    # Upstream: ReactMultiChild-test.js
    # "should warn for duplicated array keys with component stack info"
    container = Container()
    root = create_root(container)

    def App() -> object:
        return create_element(
            "ul",
            None,
            create_element("li", {"key": "c"}),
            create_element("li", {"key": "c"}),
        )

    with WarningCapture() as wc:
        root.render(create_element(App))

    wc.assert_any("Encountered two children with the same key")
    wc.assert_any("Component stack:")
    wc.assert_any("in App")
