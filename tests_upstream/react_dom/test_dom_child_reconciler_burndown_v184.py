# Translated from: packages/react-dom/src/__tests__/ReactChildReconciler-test.js
# Burndown v184: duplicate key warnings (basic) + iterable-function child guard.
from __future__ import annotations

from collections.abc import Iterator

from ryact import Component, create_element
from ryact.dev import set_dev
from ryact_dom.dom import Container
from ryact_dom.root import create_root
from ryact_testkit import WarningCapture, act


def _make_iterable_function(label: str) -> object:
    class IterableFn:
        def __init__(self, text: str) -> None:
            self._text = text

        def __call__(self) -> str:
            return self._text

        def __iter__(self) -> Iterator[str]:
            yield self._text

    return IterableFn(label)


def test_warns_for_duplicated_array_keys() -> None:
    class Row(Component):
        def render(self) -> object:
            return create_element(
                "div",
                None,
                create_element("div", {"key": "1"}),
                create_element("div", {"key": "1"}),
            )

    container = Container()
    root = create_root(container)
    set_dev(True)
    with WarningCapture() as cap, act():
        root.render(create_element(Row))
    cap.assert_any("Encountered two children with the same key")


def test_warns_for_duplicated_iterable_keys() -> None:
    class Row(Component):
        def render(self) -> object:
            kids = (create_element("div", {"key": "1"}), create_element("div", {"key": "1"}))
            return create_element("div", {"children": kids})

    container = Container()
    root = create_root(container)
    set_dev(True)
    with WarningCapture() as cap, act():
        root.render(create_element(Row))
    cap.assert_any("Encountered two children with the same key")


def test_does_not_treat_functions_as_iterables() -> None:
    iterable_fn = _make_iterable_function("foo")

    container = Container()
    root = create_root(container)
    set_dev(True)
    with WarningCapture() as cap, act():
        root.render(
            create_element(
                "div",
                None,
                create_element("h1", None, iterable_fn),
            )
        )
    cap.assert_any("Functions are not valid as a React child")
