from ryact import clone_element, create_element
from ryact.dev import set_dev
from ryact_testkit import WarningCapture


def test_should_clone_a_dom_component_with_new_props() -> None:
    # Upstream: ReactElementClone-test.js
    # "should clone a DOM component with new props"
    el = create_element("div", {"a": 1})
    cloned = clone_element(el, {"b": 2})
    assert cloned.type == "div"
    assert cloned.props["a"] == 1
    assert cloned.props["b"] == 2


def test_should_clone_a_composite_component_with_new_props() -> None:
    # Upstream: ReactElementClone-test.js
    # "should clone a composite component with new props"
    def App(**props: object) -> object:
        return create_element("div", {"text": str(props.get("msg"))})

    el = create_element(App, {"msg": "a"})
    cloned = clone_element(el, {"msg": "b"})
    assert cloned.type is App
    assert cloned.props["msg"] == "b"


def test_should_accept_children_as_rest_arguments() -> None:
    # Upstream: ReactElementClone-test.js
    # "should accept children as rest arguments"
    el = create_element("div")
    cloned = clone_element(el, None, "a", "b")
    assert cloned.props["children"] == ("a", "b")


def test_should_extract_null_key_and_ref() -> None:
    # Upstream: ReactElementClone-test.js
    # "should extract null key and ref"
    el = create_element("div", {"key": "k1", "ref": object()})
    cloned = clone_element(el, {"key": None, "ref": None})
    assert cloned.key is None
    assert cloned.ref is None


def test_does_not_warn_when_the_array_contains_a_non_element() -> None:
    # Upstream: ReactElementClone-test.js
    # "does not warn when the array contains a non-element"
    set_dev(True)
    el = create_element("div")
    with WarningCapture() as cap:
        _ = clone_element(el, None, [create_element("span", {"key": "a"}), "x"])
    assert cap.records == []


def test_does_not_warns_for_arrays_of_elements_with_keys() -> None:
    # Upstream: ReactElementClone-test.js
    # "does not warns for arrays of elements with keys"
    set_dev(True)
    el = create_element("div")
    with WarningCapture() as cap:
        _ = clone_element(el, None, [create_element("span", {"key": "a"})])
    assert cap.records == []


import pytest


def test_clone_element_throws_if_passed_none() -> None:
    # Upstream: ReactElementClone-test.js — "throws an error if passed null"
    with pytest.raises(TypeError):
        clone_element(None)  # type: ignore[arg-type]


def test_clone_element_overwrites_props() -> None:
    # Upstream: ReactElementClone-test.js — "should overwrite props"
    el = create_element("div", {"id": "a", "title": "t"})
    out = clone_element(el, {"id": "b"})
    assert out.type == "div"
    assert dict(out.props)["id"] == "b"
    assert dict(out.props)["title"] == "t"


def test_should_keep_the_original_ref_if_it_is_not_overridden() -> None:
    # Upstream: ReactElementClone-test.js
    # "should keep the original ref if it is not overridden"
    ref = object()
    el = create_element("div", {"ref": ref})
    cloned = clone_element(el, {"id": "x"})
    assert cloned.ref is ref


def test_should_steal_the_ref_if_a_new_ref_is_specified() -> None:
    # Upstream: ReactElementClone-test.js
    # "should steal the ref if a new ref is specified"
    ref1 = object()
    ref2 = object()
    el = create_element("div", {"ref": ref1})
    cloned = clone_element(el, {"ref": ref2})
    assert cloned.ref is ref2


def test_should_support_keys_and_refs() -> None:
    # Upstream: ReactElementClone-test.js
    # "should support keys and refs"
    ref = object()
    el = create_element("div", {"key": "k1", "ref": ref})
    cloned = clone_element(el, {"id": "x"})
    assert cloned.key == "k1"
    assert cloned.ref is ref


def test_should_transfer_the_key_property() -> None:
    # Upstream: ReactElementClone-test.js
    # "should transfer the key property"
    el = create_element("div", {"key": "k1"})
    cloned = clone_element(el, {"title": "t"})
    assert cloned.key == "k1"


def test_should_transfer_children() -> None:
    # Upstream: ReactElementClone-test.js
    # "should transfer children"
    el = create_element("div", None, "a")
    cloned = clone_element(el, {"id": "x"})
    assert cloned.props["children"] == ("a",)


def test_should_shallow_clone_children() -> None:
    # Upstream: ReactElementClone-test.js
    # "should shallow clone children"
    child = create_element("span")
    el = create_element("div", None, child)
    cloned = clone_element(el, None)
    assert cloned.props["children"][0] is child


def test_should_ignore_undefined_key_and_ref() -> None:
    # Upstream: ReactElementClone-test.js
    # "should ignore undefined key and ref"
    #
    # Python analogue: if key/ref are not specified in the clone config,
    # the original values remain.
    ref = object()
    el = create_element("div", {"key": "k1", "ref": ref})
    cloned = clone_element(el, {"id": "x"})
    assert cloned.key == "k1"
    assert cloned.ref is ref


def test_does_not_warn_when_the_element_is_directly_in_rest_args() -> None:
    # Upstream: ReactElementClone-test.js
    # "does not warn when the element is directly in rest args"
    set_dev(True)
    el = create_element("div")
    with WarningCapture() as cap:
        _ = clone_element(el, None, create_element("span", {"key": "a"}))
    assert cap.records == []


def test_should_override_children_if_undefined_is_provided_as_an_argument() -> None:
    # Upstream: ReactElementClone-test.js
    # "should override children if undefined is provided as an argument"
    #
    # Python analogue: passing `None` as the single explicit child clears children.
    el = create_element("div", None, "a")
    cloned = clone_element(el, None, None)
    assert cloned.props["children"] == ()


def test_throws_an_error_if_passed_undefined() -> None:
    # Upstream: ReactElementClone-test.js
    # "throws an error if passed undefined"
    #
    # Python analogue: clone_element expects an Element, so non-Element values error.
    with pytest.raises(TypeError):
        clone_element("not-an-element")  # type: ignore[arg-type]


def test_warns_for_keys_for_arrays_of_elements_in_rest_args() -> None:
    # Upstream: ReactElementClone-test.js
    # "warns for keys for arrays of elements in rest args"
    set_dev(True)
    el = create_element("div")
    with WarningCapture() as cap:
        _ = clone_element(el, None, [create_element("span"), create_element("b")])
    assert any("key" in str(r.message).lower() for r in cap.records)
