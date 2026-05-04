"""
Fragment fiber identity vs React 19 / noop parity (subset).

Ryact's keyed reconciliation does not yet match every cross-wrapper move from upstream:
switching a keyed host between a bare child and a Fragment wrapper may remount instead of
``componentDidUpdate`` (several ReactFragment-test cases stay inventory-pending until that
behavior lands).
"""

from __future__ import annotations

from typing import Any

from ryact import Component, Fragment, create_element
from ryact_testkit import WarningCapture, create_noop_root


def _snap_text(root: Any) -> str:
    return str(root.get_children_snapshot())


def _make_stateful(ops: list[str]) -> type[Component]:
    class Stateful(Component):
        def componentDidUpdate(self) -> None:
            ops.append("Update Stateful")

        def render(self) -> object:
            return create_element("div", {"text": "Hello"})

    return Stateful


def test_should_preserve_state_between_top_level_fragments() -> None:
    ops: list[str] = []
    Stateful = _make_stateful(ops)

    def Foo(*, condition: bool) -> object:
        return create_element(Fragment, None, create_element(Stateful))

    root = create_noop_root()
    root.render(create_element(Foo, {"condition": True}))
    root.flush()
    root.render(create_element(Foo, {"condition": False}))
    root.flush()
    assert ops == ["Update Stateful"]
    assert "Hello" in _snap_text(root)

    root.render(create_element(Foo, {"condition": True}))
    root.flush()
    assert ops == ["Update Stateful", "Update Stateful"]


def test_should_preserve_state_of_children_nested_at_same_level() -> None:
    ops: list[str] = []
    Stateful = _make_stateful(ops)

    def Foo(*, condition: bool) -> object:
        if condition:
            return create_element(
                Fragment,
                None,
                create_element(
                    Fragment,
                    None,
                    create_element(Fragment, None, create_element(Stateful, {"key": "a"})),
                ),
            )
        return create_element(
            Fragment,
            None,
            create_element(
                Fragment,
                None,
                create_element(
                    Fragment,
                    None,
                    create_element("div"),
                    create_element(Stateful, {"key": "a"}),
                ),
            ),
        )

    root = create_noop_root()
    root.render(create_element(Foo, {"condition": True}))
    root.flush()
    root.render(create_element(Foo, {"condition": False}))
    root.flush()
    assert ops == ["Update Stateful"]
    s = _snap_text(root)
    assert "Hello" in s

    root.render(create_element(Foo, {"condition": True}))
    root.flush()
    assert ops == ["Update Stateful", "Update Stateful"]


def test_should_not_preserve_state_of_children_if_nested_2_levels_without_siblings() -> None:
    ops: list[str] = []
    Stateful = _make_stateful(ops)

    def Foo(*, condition: bool) -> object:
        if condition:
            return create_element(Stateful, {"key": "a"})
        return create_element(
            Fragment,
            None,
            create_element(Fragment, None, create_element(Stateful, {"key": "a"})),
        )

    root = create_noop_root()
    root.render(create_element(Foo, {"condition": True}))
    root.flush()
    root.render(create_element(Foo, {"condition": False}))
    root.flush()
    assert ops == []
    root.render(create_element(Foo, {"condition": True}))
    root.flush()
    assert ops == []


def test_should_not_preserve_state_of_children_if_nested_2_levels_with_siblings() -> None:
    ops: list[str] = []
    Stateful = _make_stateful(ops)

    def Foo(*, condition: bool) -> object:
        if condition:
            return create_element(Stateful, {"key": "a"})
        return create_element(
            Fragment,
            None,
            create_element(Fragment, None, create_element(Stateful, {"key": "a"})),
            create_element("div"),
        )

    root = create_noop_root()
    root.render(create_element(Foo, {"condition": True}))
    root.flush()
    root.render(create_element(Foo, {"condition": False}))
    root.flush()
    assert ops == []
    s = _snap_text(root)
    assert "Hello" in s
    root.render(create_element(Foo, {"condition": True}))
    root.flush()
    assert ops == []


def test_should_preserve_state_between_array_nested_in_fragment_and_fragment() -> None:
    ops: list[str] = []
    Stateful = _make_stateful(ops)

    def Foo(*, condition: bool) -> object:
        if condition:
            return create_element(Fragment, None, create_element(Stateful, {"key": "a"}))
        return create_element(Fragment, None, [create_element(Stateful, {"key": "a"})])

    root = create_noop_root()
    root.render(create_element(Foo, {"condition": True}))
    root.flush()
    root.render(create_element(Foo, {"condition": False}))
    root.flush()
    assert ops == ["Update Stateful"]
    root.render(create_element(Foo, {"condition": True}))
    root.flush()
    assert ops == ["Update Stateful", "Update Stateful"]


def test_should_not_preserve_state_between_array_nested_in_fragment_and_double_nested_fragment() -> None:
    ops: list[str] = []
    Stateful = _make_stateful(ops)

    def Foo(*, condition: bool) -> object:
        if condition:
            return create_element(Fragment, None, [create_element(Stateful, {"key": "a"})])
        return create_element(
            Fragment,
            None,
            create_element(Fragment, None, create_element(Stateful, {"key": "a"})),
        )

    root = create_noop_root()
    root.render(create_element(Foo, {"condition": True}))
    root.flush()
    root.render(create_element(Foo, {"condition": False}))
    root.flush()
    assert ops == []
    root.render(create_element(Foo, {"condition": True}))
    root.flush()
    assert ops == []


def test_should_not_preserve_state_of_children_when_the_keys_are_different() -> None:
    ops: list[str] = []
    Stateful = _make_stateful(ops)

    def Foo(*, condition: bool) -> object:
        if condition:
            return create_element(Fragment, {"key": "a"}, create_element(Stateful))
        return create_element(
            Fragment,
            {"key": "b"},
            create_element(Stateful),
            create_element("span", {"text": "World"}),
        )

    root = create_noop_root()
    root.render(create_element(Foo, {"condition": True}))
    root.flush()
    root.render(create_element(Foo, {"condition": False}))
    root.flush()
    assert ops == []
    s = _snap_text(root)
    assert "Hello" in s and "World" in s
    root.render(create_element(Foo, {"condition": True}))
    root.flush()
    assert ops == []


def test_should_preserve_state_with_reordering_in_multiple_levels() -> None:
    ops: list[str] = []
    Stateful = _make_stateful(ops)

    def Foo(*, condition: bool) -> object:
        if condition:
            return create_element(
                "div",
                None,
                create_element(
                    Fragment,
                    {"key": "c"},
                    create_element("span", {"text": "foo"}),
                    create_element(
                        "div",
                        {"key": "b"},
                        create_element(Stateful, {"key": "a"}),
                    ),
                ),
                create_element("span", {"text": "boop"}),
            )
        return create_element(
            "div",
            None,
            create_element("span", {"text": "beep"}),
            create_element(
                Fragment,
                {"key": "c"},
                create_element(
                    "div",
                    {"key": "b"},
                    create_element(Stateful, {"key": "a"}),
                ),
                create_element("span", {"text": "bar"}),
            ),
        )

    root = create_noop_root()
    root.render(create_element(Foo, {"condition": True}))
    root.flush()
    root.render(create_element(Foo, {"condition": False}))
    root.flush()
    assert ops == ["Update Stateful"]
    s = _snap_text(root)
    assert "beep" in s and "Hello" in s and "bar" in s
    root.render(create_element(Foo, {"condition": True}))
    root.flush()
    assert ops == ["Update Stateful", "Update Stateful"]
    s2 = _snap_text(root)
    assert "foo" in s2 and "Hello" in s2 and "boop" in s2


def test_should_not_preserve_state_when_switching_nested_unkeyed_fragment_to_passthrough() -> None:
    ops: list[str] = []
    Stateful = _make_stateful(ops)

    def Passthrough(**props: Any) -> object:
        return props.get("children")

    def Foo(*, condition: bool) -> object:
        if condition:
            return create_element(
                Fragment,
                None,
                create_element(Fragment, None, create_element(Stateful)),
            )
        return create_element(
            Fragment,
            None,
            create_element(Passthrough, {"children": create_element(Stateful)}),
        )

    root = create_noop_root()
    root.render(create_element(Foo, {"condition": True}))
    root.flush()
    root.render(create_element(Foo, {"condition": False}))
    root.flush()
    assert ops == []
    root.render(create_element(Foo, {"condition": True}))
    root.flush()
    assert ops == []


def test_should_not_preserve_state_when_switching_nested_keyed_fragment_to_passthrough() -> None:
    ops: list[str] = []
    Stateful = _make_stateful(ops)

    def Passthrough(**props: Any) -> object:
        return props.get("children")

    def Foo(*, condition: bool) -> object:
        if condition:
            return create_element(
                Fragment,
                None,
                create_element(Fragment, {"key": "a"}, create_element(Stateful)),
            )
        return create_element(
            Fragment,
            None,
            create_element(Passthrough, {"children": create_element(Stateful)}),
        )

    root = create_noop_root()
    root.render(create_element(Foo, {"condition": True}))
    root.flush()
    root.render(create_element(Foo, {"condition": False}))
    root.flush()
    assert ops == []
    root.render(create_element(Foo, {"condition": True}))
    root.flush()
    assert ops == []


def test_should_not_preserve_state_when_switching_nested_keyed_array_to_passthrough() -> None:
    ops: list[str] = []
    Stateful = _make_stateful(ops)

    def Passthrough(**props: Any) -> object:
        return props.get("children")

    def Foo(*, condition: bool) -> object:
        if condition:
            return create_element(Fragment, None, [create_element(Stateful, {"key": "a"})])
        return create_element(
            Fragment,
            None,
            create_element(Passthrough, {"children": create_element(Stateful)}),
        )

    root = create_noop_root()
    root.render(create_element(Foo, {"condition": True}))
    root.flush()
    root.render(create_element(Foo, {"condition": False}))
    root.flush()
    assert ops == []


def test_should_not_preserve_state_when_switching_to_keyed_fragment_from_array() -> None:
    ops: list[str] = []
    Stateful = _make_stateful(ops)

    def Foo(*, condition: bool) -> object:
        if condition:
            return create_element(
                "div",
                None,
                create_element(Fragment, {"key": "foo"}, create_element(Stateful)),
                create_element("span"),
            )
        return create_element(
            "div",
            None,
            [create_element(Stateful)],
            create_element("span"),
        )

    root = create_noop_root()
    root.render(create_element(Foo, {"condition": True}))
    root.flush()
    with WarningCapture() as wc:
        root.render(create_element(Foo, {"condition": False}))
        root.flush()
    wc.assert_any('unique "key"')
    assert ops == []
    assert "Hello" in _snap_text(root)

    root.render(create_element(Foo, {"condition": True}))
    root.flush()
    assert ops == []


def test_should_preserve_state_when_it_does_not_change_positions() -> None:
    ops: list[str] = []
    Stateful = _make_stateful(ops)

    def Foo(*, condition: bool) -> object:
        if condition:
            return [
                create_element("span"),
                create_element(Fragment, None, create_element(Stateful)),
            ]
        return [
            create_element("span"),
            create_element(Fragment, None, create_element(Stateful)),
        ]

    root = create_noop_root()
    with WarningCapture() as wc:
        root.render(create_element(Foo, {"condition": True}))
        root.flush()
    wc.assert_any('unique "key"')
    with WarningCapture() as wc2:
        root.render(create_element(Foo, {"condition": False}))
        root.flush()
    wc2.assert_any('unique "key"')
    assert ops == ["Update Stateful"]
    assert "Hello" in _snap_text(root)

    with WarningCapture() as wc3:
        root.render(create_element(Foo, {"condition": True}))
        root.flush()
    wc3.assert_any('unique "key"')
    assert ops == ["Update Stateful", "Update Stateful"]
