# Translated from: packages/react-dom/src/__tests__/ReactMultiChild-test.js
# Burndown v164: reconciliation warnings, iterables, owners, lifecycle ordering.
from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from ryact import Component, create_element
from ryact.concurrent import Fragment
from ryact.dev import is_dev, set_dev
from ryact_dom.children_expansion import reset_dom_children_warning_state
from ryact_dom.dom import Container, ElementNode, TextNode
from ryact_dom.root import create_root
from ryact_testkit import WarningCapture


@pytest.fixture(autouse=True)
def _dev_and_reset() -> Iterator[None]:
    prev = is_dev()
    set_dev(True)
    reset_dom_children_warning_state()
    yield
    reset_dom_children_warning_state()
    set_dev(prev)


def _text(container: Container) -> str:
    def walk(node: ElementNode | TextNode) -> str:
        if isinstance(node, TextNode):
            return node.text
        return "".join(walk(ch) if isinstance(ch, (ElementNode, TextNode)) else "" for ch in node.children)

    return "".join(walk(ch) if isinstance(ch, (ElementNode, TextNode)) else "" for ch in container.root.children)


def test_should_not_replace_children_with_different_owners() -> None:
    mounts: list[int] = []
    unmounts: list[int] = []

    class MockComponent(Component):
        def componentDidMount(self) -> None:
            mounts.append(1)

        def componentWillUnmount(self) -> None:
            unmounts.append(1)

        def render(self) -> object:
            return create_element("span")

    class WrapperComponent(Component):
        def render(self) -> object:
            children = self.props.get("children")
            if children:
                return children
            return create_element(MockComponent)

    container = Container()
    root = create_root(container)

    root.render(create_element(WrapperComponent))
    assert len(mounts) == 1
    assert len(unmounts) == 0

    root.render(create_element(WrapperComponent, None, create_element(MockComponent)))
    assert len(mounts) == 1
    assert len(unmounts) == 0


def test_prepares_new_children_before_unmounting_old() -> None:
    log: list[str] = []

    class Spy(Component):
        def componentWillMount(self) -> None:
            log.append(f"{self.props['name']} componentWillMount")

        def render(self) -> object:
            log.append(f"{self.props['name']} render")
            return create_element("div")

        def componentDidMount(self) -> None:
            log.append(f"{self.props['name']} componentDidMount")

        def componentWillUnmount(self) -> None:
            log.append(f"{self.props['name']} componentWillUnmount")

    def spy_a_one(_props: object) -> object:
        return create_element(Spy, {"name": "oneA"})

    def spy_a_two(_props: object) -> object:
        return create_element(Spy, {"name": "twoA"})

    def spy_b_one(_props: object) -> object:
        return create_element(Spy, {"name": "oneB"})

    def spy_b_two(_props: object) -> object:
        return create_element(Spy, {"name": "twoB"})

    container = Container()
    root = create_root(container)

    root.render(
        create_element(
            Fragment,
            None,
            create_element(spy_a_one, {"key": "1"}),
            create_element(spy_a_two, {"key": "2"}),
        )
    )
    root.render(
        create_element(
            Fragment,
            None,
            create_element(spy_b_one, {"key": "1"}),
            create_element(spy_b_two, {"key": "2"}),
        )
    )

    assert log == [
        "oneA componentWillMount",
        "oneA render",
        "twoA componentWillMount",
        "twoA render",
        "oneA componentDidMount",
        "twoA componentDidMount",
        "oneB componentWillMount",
        "oneB render",
        "twoB componentWillMount",
        "twoB render",
        "oneA componentWillUnmount",
        "twoA componentWillUnmount",
        "oneB componentDidMount",
        "twoB componentDidMount",
    ]


def test_should_not_warn_for_using_generator_functions_as_components() -> None:
    def Foo() -> Any:
        yield "Hello"
        yield "World"

    container = Container()
    root = create_root(container)
    with WarningCapture() as cap:
        root.render(create_element(Foo))
    assert not cap.messages
    assert _text(container) == "HelloWorld"


def test_should_warn_for_using_generators_as_children_props() -> None:
    def get_children() -> Any:
        yield "Hello"
        yield "World"

    def Foo(_props: object) -> object:
        return create_element("div", None, get_children())

    container = Container()
    root = create_root(container)
    with WarningCapture() as cap:
        root.render(create_element(Foo))
    cap.assert_any("Using Iterators as children is unsupported")
    cap.assert_any("in Foo")
    assert _text(container) == "HelloWorld"

    with WarningCapture() as cap2:
        root.render(create_element(Foo))
    assert not cap2.messages


def test_should_warn_for_using_other_types_of_iterators_as_children() -> None:
    class Foo(Component):
        def render(self) -> object:
            class Seq:
                def __init__(self) -> None:
                    self._i = 0

                def __iter__(self) -> Seq:
                    return self

                def __next__(self) -> str:
                    if self._i == 0:
                        self._i = 1
                        return "Hello"
                    if self._i == 1:
                        self._i = 2
                        return "World"
                    raise StopIteration

            return Seq()

    container = Container()
    root = create_root(container)
    with WarningCapture() as cap:
        root.render(create_element(Foo))
    cap.assert_any("Using Iterators as children is unsupported")
    cap.assert_any("in Foo")
    assert _text(container) == "HelloWorld"

    with WarningCapture() as cap2:
        root.render(create_element(Foo))
    assert not cap2.messages


def test_should_warn_for_using_maps_as_children_with_owner_info() -> None:
    class MapChildren:
        _ryact_map_children = True

        def __init__(self, items: list[tuple[str, int]]) -> None:
            self._items = items

        def __iter__(self) -> Iterator[tuple[str, int]]:
            return iter(self._items)

    class Parent(Component):
        def render(self) -> object:
            return create_element(
                "div",
                None,
                MapChildren([("foo", 0), ("bar", 1)]),
            )

    container = Container()
    root = create_root(container)
    with WarningCapture() as cap:
        root.render(create_element(Parent))
    cap.assert_any("Using Maps as children is not supported")
    cap.assert_any("in Parent")


def test_should_not_warn_for_using_generators_in_legacy_iterables() -> None:
    class LegacyIterable:
        def __iter__(self) -> Any:
            yield "Hello"
            yield "World"

    def Foo(_props: object) -> object:
        return LegacyIterable()

    container = Container()
    root = create_root(container)
    with WarningCapture() as cap:
        root.render(create_element(Foo))
        root.render(create_element(Foo))
    assert not cap.messages
    assert _text(container) == "HelloWorld"


def test_should_not_warn_for_using_generators_in_modern_iterables() -> None:
    class ModernIterable:
        def __iter__(self) -> Any:
            yield "Hello"
            yield "World"

    def Foo(_props: object) -> object:
        return ModernIterable()

    container = Container()
    root = create_root(container)
    with WarningCapture() as cap:
        root.render(create_element(Foo))
        root.render(create_element(Foo))
    assert not cap.messages
    assert _text(container) == "HelloWorld"


def test_should_warn_for_duplicated_iterable_keys_with_component_stack_info() -> None:
    class CustomIterable:
        def __init__(self, items: list[object]) -> None:
            self._items = items

        def __iter__(self) -> Iterator[object]:
            return iter(self._items)

    class WrapperComponent(Component):
        def render(self) -> object:
            return self.props.get("children")

    class Parent(Component):
        def render(self) -> object:
            return create_element(
                "div",
                None,
                create_element(WrapperComponent, {"children": self.props.get("children")}),
            )

    container = Container()
    root = create_root(container)

    root.render(create_element(Parent, {"children": CustomIterable([])}))

    dup_children = CustomIterable(
        [
            create_element("div", {"key": "1"}),
            create_element("div", {"key": "1"}),
        ]
    )
    with WarningCapture() as cap:
        root.render(create_element(Parent, {"children": dup_children}))
    cap.assert_any("Encountered two children with the same key")
    cap.assert_any("Component stack:")
    cap.assert_any("in Parent")
