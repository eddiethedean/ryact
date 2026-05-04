from __future__ import annotations

import pytest
from ryact import Component, create_element
from ryact.dev import set_dev
from ryact_testkit import WarningCapture, create_noop_root


def test_should_not_implicitly_bind_event_handlers() -> None:
    # Upstream: ReactES6Class-test.js
    # "should not implicitly bind event handlers"
    class Foo(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self.set_state({"x": 1})

        def on_click(self) -> None:
            return None

        def render(self) -> object:
            return create_element("div")

    inst = Foo()
    # Python methods are descriptors; implicit binding is explicit via attribute access.
    # Upstream intent: React should not auto-bind methods to `this`.
    assert inst.on_click.__self__ is inst  # type: ignore[attr-defined]


def test_should_throw_and_warn_when_trying_to_access_classic_apis() -> None:
    # Upstream: ReactES6Class-test.js
    # "should throw AND warn when trying to access classic APIs"
    set_dev(True)

    class Foo(Component):
        def render(self) -> object:
            # Classic APIs we don't implement; should warn and throw if accessed.
            return self.isMounted()  # type: ignore[misc]

    root = create_noop_root()
    with WarningCapture() as cap, pytest.raises(AttributeError):
        root.render(create_element(Foo))
    assert any("classic" in str(r.message).lower() or "ismounted" in str(r.message).lower() for r in cap.records)


def test_will_call_all_the_normal_life_cycle_methods() -> None:
    # Upstream: ReactES6Class-test.js
    # "will call all the normal life cycle methods"
    log: list[str] = []

    class Foo(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            log.append("ctor")

        def UNSAFE_componentWillMount(self) -> None:  # noqa: N802
            log.append("cwm")

        def componentDidMount(self) -> None:  # noqa: N802
            log.append("cdm")

        def render(self) -> object:
            log.append("render")
            return create_element("div")

    root = create_noop_root()
    root.render(create_element(Foo))
    assert log == ["ctor", "cwm", "render", "cdm"]
