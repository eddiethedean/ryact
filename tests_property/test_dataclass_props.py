from __future__ import annotations

from dataclasses import dataclass

from ryact import create_element


@dataclass
class Props:
    id: str = "a"
    key: str | None = None
    ref: object | None = None
    children: tuple[object, ...] = ()


def test_dataclass_props_converts_to_dict() -> None:
    el = create_element("div", Props(id="x"))
    assert el.props["id"] == "x"


def test_dataclass_props_kwargs_override_fields() -> None:
    el = create_element("div", Props(id="x"), id="y")
    assert el.props["id"] == "y"


def test_dataclass_children_field_is_used_when_no_positional_children() -> None:
    el = create_element("div", Props(children=("a", "b")))
    assert el.props["children"] == ("a", "b")


def test_positional_children_override_dataclass_children() -> None:
    el = create_element("div", Props(children=("a",)), "b")
    assert el.props["children"] == ("b",)


def test_dataclass_key_and_ref_extract() -> None:
    ref = object()
    el = create_element("div", Props(key="k", ref=ref))
    assert el.key == "k"
    assert el.ref is ref
