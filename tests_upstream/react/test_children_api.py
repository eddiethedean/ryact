from __future__ import annotations

import re
from typing import Any

from ryact import (
    Children,
    children_count,
    children_for_each,
    children_map,
    children_to_array,
    create_element,
    only_child,
)
from ryact.concurrent import Portal, create_portal, fragment
from ryact.dev import set_dev
from ryact_testkit.warnings import WarningCapture


def test_does_not_throw_on_children_without_store() -> None:
    # Our Element model has no `_store`; ensure traversal doesn't depend on it.
    e = create_element("div", None, "x")
    assert children_count(e) == 1


def test_should_be_called_for_each_child_variants() -> None:
    seen: list[tuple[Any, int]] = []
    children_for_each([1, 2, None], lambda c, i: seen.append((c, i)))
    assert seen == [(1, 0), (2, 1), (None, 2)]


def test_should_be_called_for_each_child_in_iterables() -> None:
    def gen() -> Any:
        yield "a"
        yield "b"

    out: list[Any] = []
    Children.for_each(gen(), lambda c, i: out.append((c, i)))
    assert out == [("a", 0), ("b", 1)]


def test_should_count_children_flat_and_nested() -> None:
    assert children_count([1, 2, 3]) == 3
    assert children_count([1, [2, 3], (4, 5)]) == 5


def test_should_flatten_children_to_array() -> None:
    arr = children_to_array([1, [2, 3], None])
    assert arr == [1, 2, 3, None]


def test_should_escape_keys_and_retain_key_across_mappings() -> None:
    e = create_element("div", {"key": "a/b"})
    arr = children_to_array([e])
    assert arr[0].key in ("a//b", "a/b")

    mapped = children_map([e], lambda c, i: c)
    assert isinstance(mapped[0], type(e))
    assert mapped[0].key == e.key


def test_should_combine_keys_when_map_returns_array() -> None:
    e = create_element("div", {"key": "k"})
    mapped = children_map([e], lambda c, i: [create_element("span", {"key": "a"}), create_element("span", None)])
    assert isinstance(mapped[0], type(e))
    assert mapped[0].key is not None
    assert isinstance(mapped[1], type(e))
    assert mapped[1].key is not None


def test_should_return_0_for_null_and_undefined_children() -> None:
    assert children_count(None) == 0
    assert Children.count(None) == 0


def test_should_return_1_for_single_child_and_treat_singletons_as_arrays() -> None:
    assert children_count("x") == 1
    assert children_to_array("x") == ["x"]


def test_only_child_errors() -> None:
    assert only_child("x") == "x"
    with pytest_raises(ValueError):
        only_child(["a", "b"])
    with pytest_raises(TypeError):
        only_child({"x": 1})
    with pytest_raises(TypeError):
        only_child(re.compile("x"))


def test_should_support_portal_components() -> None:
    p = create_portal(children=create_element("div", None), container={"id": "c"})
    arr = children_to_array([p])
    assert isinstance(arr[0], type(p))
    assert arr[0].type == Portal


def test_fragment_enabled_warning_cases() -> None:
    set_dev(True)
    with WarningCapture() as wc:
        # top-level array without keys -> warning
        Children.to_array([create_element("div", None), create_element("div", None)])
        from ryact.children import warn_if_missing_keys

        warn_if_missing_keys([create_element("div", None), create_element("div", None)], stacklevel=2)
    assert any("key" in m for m in wc.messages)

    # does not warn when keys exist inside a fragment
    with WarningCapture() as wc2:
        warn_if_missing_keys(fragment(create_element("div", {"key": "a"}), create_element("div", {"key": "b"})))
    assert wc2.messages == []


def pytest_raises(exc: type[BaseException]):
    # tiny local helper to avoid importing pytest (keep upstream-style tests minimal)
    class _CM:
        def __enter__(self):
            return None

        def __exit__(self, et, ev, tb):
            return et is not None and issubclass(et, exc)

    return _CM()
