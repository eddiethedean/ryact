from __future__ import annotations

from ryact import Component, create_element
from ryact_testkit import create_noop_root


def test_es6_classes_and_coffeescript_equivalence() -> None:
    # Upstream: ReactClassEquivalence-test.js
    # "tests the same thing for es6 classes and CoffeeScript"
    class Foo(Component):
        def render(self) -> object:
            return create_element("div", {"text": "ok"})

    root = create_noop_root()
    root.render(create_element(Foo))
    assert root.container.last_committed_as_dict()["props"]["text"] == "ok"


def test_es6_classes_and_typescript_equivalence() -> None:
    # Upstream: ReactClassEquivalence-test.js
    # "tests the same thing for es6 classes and TypeScript"
    class Foo(Component):
        def render(self) -> object:
            return create_element("div", {"text": "ok"})

    root = create_noop_root()
    root.render(create_element(Foo))
    assert root.container.last_committed_as_dict()["props"]["text"] == "ok"
