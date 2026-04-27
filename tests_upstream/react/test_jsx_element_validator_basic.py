from __future__ import annotations

from ryact import Fragment, create_element
from ryact.dev import set_dev
from ryact_testkit import WarningCapture


def test_does_not_warn_when_the_child_array_contains_non_elements() -> None:
    # Upstream: ReactJSXElementValidator-test.js
    # "does not warn when the child array contains non-elements"
    set_dev(True)
    with WarningCapture() as cap:
        _ = create_element("div", None, [create_element("span", {"key": "a"}), "x"])
    assert cap.records == []


def test_does_not_warn_when_the_element_is_directly_as_children() -> None:
    # Upstream: ReactJSXElementValidator-test.js
    # "does not warn when the element is directly as children"
    set_dev(True)
    with WarningCapture() as cap:
        _ = create_element("div", None, create_element("span", {"key": "a"}))
    assert cap.records == []


def test_does_not_warn_for_arrays_of_elements_with_keys() -> None:
    # Upstream: ReactJSXElementValidator-test.js
    # "does not warn for arrays of elements with keys"
    set_dev(True)
    with WarningCapture() as cap:
        _ = create_element(
            "div",
            None,
            [
                create_element("span", {"key": "a"}),
                create_element("b", {"key": "b"}),
            ],
        )
    assert cap.records == []


def test_warns_for_keys_for_arrays_of_elements_in_children_position() -> None:
    # Upstream: ReactJSXElementValidator-test.js
    # "warns for keys for arrays of elements in children position"
    set_dev(True)
    with WarningCapture() as cap:
        _ = create_element("div", None, [create_element("span"), create_element("b")])
    assert any("key" in str(r.message).lower() for r in cap.records)


def test_warns_for_fragments_with_illegal_attributes() -> None:
    # Upstream: ReactJSXElementValidator-test.js
    # "warns for fragments with illegal attributes"
    set_dev(True)
    with WarningCapture() as cap:
        _ = create_element(Fragment, {"className": "illegal"}, "child")
    assert any("fragment" in str(r.message).lower() for r in cap.records)
    assert any("classname" in str(r.message).lower() for r in cap.records)


def test_warns_for_fragments_with_refs() -> None:
    # Upstream: ReactJSXElementValidator-test.js
    # "warns for fragments with refs"
    set_dev(True)
    with WarningCapture() as cap:
        _ = create_element(Fragment, {"ref": object()}, "child")
    assert any("fragment" in str(r.message).lower() for r in cap.records)
    assert any("ref" in str(r.message).lower() for r in cap.records)

