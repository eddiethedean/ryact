from __future__ import annotations

from ryact import Component, create_element
from ryact_testkit import create_noop_root


def _assert_basic_class_semantics(Cls: type[Component]) -> None:
    root = create_noop_root()
    root.render(create_element(Cls, {"label": "A"}))
    assert root.container.last_committed == {
        "type": "div",
        "key": None,
        "props": {"text": "A:1"},
        "children": [],
    }


def test_tests_the_same_thing_for_es6_classes_and_coffeescript() -> None:
    # Upstream: ReactClassEquivalence-test.js
    # "tests the same thing for es6 classes and CoffeeScript"
    #
    # Python analogue: a normal class definition and a dynamically-created class
    # (similar to how transpiled/classic codepaths can differ) should behave the same.
    class Normal(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self.set_state({"n": 1})

        def render(self) -> object:
            return create_element("div", {"text": f"{self.props['label']}:{self.state['n']}"})

    Dynamic = type(
        "Dynamic",
        (Component,),
        {
            "__init__": lambda self, **props: (
                Component.__init__(self, **props),
                self.set_state({"n": 1}),
            )[-1],
            "render": lambda self: create_element("div", {"text": f"{self.props['label']}:{self.state['n']}"}),
        },
    )

    _assert_basic_class_semantics(Normal)
    _assert_basic_class_semantics(Dynamic)


def test_tests_the_same_thing_for_es6_classes_and_typescript() -> None:
    # Upstream: ReactClassEquivalence-test.js
    # "tests the same thing for es6 classes and TypeScript"
    #
    # Python analogue: a class with explicit type-ish structure (same runtime) behaves
    # the same as a minimal class.
    class TypedLike(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self.set_state({"n": 1})

        def render(self) -> object:
            return create_element("div", {"text": f"{self.props['label']}:{self.state['n']}"})

    _assert_basic_class_semantics(TypedLike)
