from __future__ import annotations

from ryact import create_element, h


def test_create_element_children_are_flattened_one_level() -> None:
    el = create_element("div", None, "a", ["b", "c"], ("d",))
    assert el.type == "div"
    assert el.props["children"] == ("a", "b", "c", "d")


def test_create_element_children_do_not_deep_flatten_nested_sequences() -> None:
    el = create_element("div", children=["a", ["b", ["c"]]])
    assert el.props["children"] == ("a", "b", ["c"])


def test_create_element_children_positional_override_children_prop() -> None:
    el = create_element("div", {"children": ["x", "y"]}, "a", "b")
    assert el.props["children"] == ("a", "b")


def test_create_element_children_prop_is_preserved_when_no_rest_args_are_provided() -> None:
    el = create_element("div", {"children": ["x", "y"]})
    assert el.props["children"] == ("x", "y")


def test_create_element_children_are_overridden_when_none_is_provided_as_an_argument() -> None:
    el = create_element("div", {"children": ["x", "y"]}, None)
    assert el.props["children"] == (None,)


def test_create_element_extracts_key_and_ref_from_props() -> None:
    ref = object()
    el = create_element("div", {"key": "k1", "ref": ref, "id": "x"})
    assert el.key == "k1"
    assert el.ref is ref
    assert el.props["id"] == "x"
    assert "key" not in el.props
    assert "ref" not in el.props


def test_create_element_extracts_key_and_ref_from_kwargs() -> None:
    ref = object()
    el = create_element("div", None, key="k1", ref=ref, id="x")
    assert el.key == "k1"
    assert el.ref is ref
    assert el.props["id"] == "x"
    assert "key" not in el.props
    assert "ref" not in el.props


def test_create_element_coerces_key_to_string() -> None:
    el = create_element("div", None, key=5)
    assert el.key == "5"


def test_create_element_extracts_null_key() -> None:
    el = create_element("div", None, key=None)
    assert el.key is None


def test_create_element_ignores_missing_key_and_ref() -> None:
    el = create_element("div", {"id": "x"})
    assert el.key is None
    assert el.ref is None
    assert el.props["id"] == "x"


def test_create_element_merges_pythonic_kwargs() -> None:
    el = create_element("div", None, "a", id="x", tab_index=1)
    assert el.props["id"] == "x"
    assert el.props["tab_index"] == 1
    assert el.props["children"] == ("a",)


def test_create_element_kwargs_override_props_dict() -> None:
    el = create_element("div", {"id": "a"}, id="b")
    assert el.props["id"] == "b"


def test_create_element_does_not_mutate_props_dict() -> None:
    props = {"id": "x", "children": ["a"]}
    el = create_element("div", props, "b")
    assert el.props["children"] == ("b",)
    assert props == {"id": "x", "children": ["a"]}


def test_create_element_children_kwarg_is_normalized() -> None:
    el = create_element("div", children=["a", ["b", "c"]])
    assert el.props["children"] == ("a", "b", "c")


def test_h_alias_matches_create_element() -> None:
    a = h("span", None, "x", title="t")
    b = create_element("span", None, "x", title="t")
    assert a.props == b.props
