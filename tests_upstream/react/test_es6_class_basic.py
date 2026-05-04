from __future__ import annotations

from collections.abc import Callable
from typing import cast

from ryact import Component, create_element
from ryact.dev import set_dev
from ryact_testkit import create_noop_root
from ryact_testkit.warnings import WarningCapture


def test_renders_a_simple_stateless_component_with_prop() -> None:
    # Upstream: ReactES6Class-test.js
    # "renders a simple stateless component with prop"
    def Hello(**props: object) -> object:
        return create_element("div", {"text": f"Hello {props['name']}"})

    root = create_noop_root()
    root.render(create_element(Hello, {"name": "World"}))
    assert root.container.last_committed == {
        "type": "div",
        "key": None,
        "props": {"text": "Hello World"},
        "children": [],
    }


def test_renders_based_on_state_using_props_in_the_constructor() -> None:
    # Upstream: ReactES6Class-test.js
    # "renders based on state using props in the constructor"
    class Greeter(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self.set_state({"greet": f"Hello {self.props['name']}"})

        def render(self) -> object:
            return create_element("div", {"text": str(self.state["greet"])})

    root = create_noop_root()
    root.render(create_element(Greeter, {"name": "Alice"}))
    assert root.container.last_committed["props"]["text"] == "Hello Alice"


def test_renders_based_on_state_using_initial_values_in_this_props() -> None:
    # Upstream: ReactES6Class-test.js
    # "renders based on state using initial values in this.props"
    class Counter(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self.set_state({"count": int(self.props["initial"])})

        def render(self) -> object:
            return create_element("div", {"count": int(self.state["count"])})

    root = create_noop_root()
    root.render(create_element(Counter, {"initial": 3}))
    assert root.container.last_committed["props"]["count"] == 3


def test_setstate_through_an_event_handler() -> None:
    # Upstream: ReactES6Class-test.js
    # "setState through an event handler"
    api: dict[str, object] = {}

    class Button(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self.set_state({"clicked": False})
            api["click"] = self.on_click

        def on_click(self) -> None:
            self.set_state({"clicked": True})

        def render(self) -> object:
            return create_element("div", {"clicked": bool(self.state["clicked"])})

    root = create_noop_root()
    root.render(create_element(Button))
    assert root.container.last_committed["props"]["clicked"] is False

    cast(Callable[[], None], api["click"])()
    root.flush()
    assert root.container.last_committed["props"]["clicked"] is True


def test_renders_only_once_when_setting_state_in_componentwillmount() -> None:
    # Upstream: ReactES6Class-test.js
    # "renders only once when setting state in componentWillMount"
    log: list[str] = []

    class Foo(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self.set_state({"step": 0})

        def UNSAFE_componentWillMount(self) -> None:  # noqa: N802
            self.set_state({"step": 1})

        def render(self) -> object:
            log.append(f"render:{self.state['step']}")
            return create_element("div", {"step": int(self.state["step"])})

    root = create_noop_root()
    root.render(create_element(Foo))
    assert log == ["render:1"]
    assert root.container.last_committed["props"]["step"] == 1


def test_preserves_the_name_of_the_class_for_use_in_error_messages() -> None:
    # Upstream: ReactES6Class-test.js
    # "preserves the name of the class for use in error messages"
    class Exploder(Component):
        def render(self) -> object:
            raise RuntimeError("boom")

    root = create_noop_root()
    try:
        root.render(create_element(Exploder))
        raise AssertionError("expected render to throw")
    except RuntimeError as err:
        # We attach a component stack to exceptions thrown during render.
        assert "Exploder" in str(err)


def test_does_not_warn_about_getinitialstate_on_class_components_if_state_is_also_defined() -> None:
    # Upstream: ReactES6Class-test.js
    # "does not warn about getInitialState() on class components if state is also defined."
    class HasGetInitialState(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self.set_state({"ok": True})

        def getInitialState(self) -> object:  # noqa: N802
            return {"ignored": True}

        def render(self) -> object:
            return create_element("div", {"ok": bool(self.state.get("ok"))})

    root = create_noop_root()
    with WarningCapture() as cap:
        root.render(create_element(HasGetInitialState))
    # If/when we implement these classic API warnings, this case should remain quiet.
    assert not cap.records


def test_renders_using_forceupdate_even_when_there_is_no_state() -> None:
    # Upstream: ReactES6Class-test.js
    # "renders using forceUpdate even when there is no state"
    api: dict[str, object] = {}
    renders: list[str] = []

    class Foo(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            api["force"] = self.forceUpdate

        def render(self) -> object:
            renders.append("render")
            return create_element("div", {"n": len(renders)})

    root = create_noop_root()
    root.render(create_element(Foo))
    assert renders == ["render"]
    assert root.container.last_committed["props"]["n"] == 1

    cast(Callable[[], None], api["force"])()
    root.flush()
    assert renders == ["render", "render"]
    assert root.container.last_committed["props"]["n"] == 2


def test_sets_initial_state_with_value_returned_by_static_getderivedstatefromprops() -> None:
    # Upstream: ReactES6Class-test.js
    # "sets initial state with value returned by static getDerivedStateFromProps"
    class WithGDSFP(Component):
        @staticmethod
        def getDerivedStateFromProps(props: object, _state: object) -> object:  # noqa: N802
            return {"derived": cast(dict[str, object], props)["value"]}

        def render(self) -> object:
            return create_element("div", {"derived": self.state.get("derived")})

    root = create_noop_root()
    root.render(create_element(WithGDSFP, {"value": 123}))
    assert root.container.last_committed["props"]["derived"] == 123


def test_renders_updated_state_with_values_returned_by_static_getderivedstatefromprops() -> None:
    # Upstream: ReactES6Class-test.js
    # "renders updated state with values returned by static getDerivedStateFromProps"
    class WithGDSFP(Component):
        @staticmethod
        def getDerivedStateFromProps(props: object, _state: object) -> object:  # noqa: N802
            return {"derived": cast(dict[str, object], props)["value"]}

        def render(self) -> object:
            return create_element("div", {"derived": self.state.get("derived")})

    root = create_noop_root()
    root.render(create_element(WithGDSFP, {"value": 1}))
    assert root.container.last_committed["props"]["derived"] == 1

    root.render(create_element(WithGDSFP, {"value": 2}))
    assert root.container.last_committed["props"]["derived"] == 2


def test_updates_initial_state_with_values_returned_by_static_getderivedstatefromprops() -> None:
    # Upstream: ReactES6Class-test.js
    # "updates initial state with values returned by static getDerivedStateFromProps"
    class WithGDSFP(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self.set_state({"base": "x"})

        @staticmethod
        def getDerivedStateFromProps(props: object, _state: object) -> object:  # noqa: N802
            return {"derived": cast(dict[str, object], props)["value"]}

        def render(self) -> object:
            return create_element(
                "div",
                {"base": self.state.get("base"), "derived": self.state.get("derived")},
            )

    root = create_noop_root()
    root.render(create_element(WithGDSFP, {"value": 5}))
    assert root.container.last_committed["props"] == {"base": "x", "derived": 5}


def test_warns_if_getderivedstatefromprops_is_not_static() -> None:
    # Upstream: ReactES6Class-test.js
    # "warns if getDerivedStateFromProps is not static"
    set_dev(True)

    class Bad(Component):
        def getDerivedStateFromProps(self, _props: object, _state: object) -> object:  # noqa: N802
            return {"x": 1}

        def render(self) -> object:
            return create_element("div")

    root = create_noop_root()
    with WarningCapture() as cap:
        root.render(create_element(Bad))
    assert any("getderivedstatefromprops" in str(r.message).lower() for r in cap.records)


def test_should_warn_with_non_object_in_the_initial_state_property() -> None:
    # Upstream: ReactES6Class-test.js
    # "should warn with non-object in the initial state property"
    set_dev(True)

    class Bad(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            # Simulate user assigning an invalid state shape.
            self._state = 123  # type: ignore[assignment]

        def render(self) -> object:
            return create_element("div")

    root = create_noop_root()
    with WarningCapture() as cap:
        root.render(create_element(Bad))
    assert any("initial state" in str(r.message).lower() for r in cap.records)


def test_warns_if_getderivedstatefromerror_is_not_static() -> None:
    # Upstream: ReactES6Class-test.js
    # "warns if getDerivedStateFromError is not static"
    set_dev(True)

    class Boundary(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self.set_state({"error": False})

        def getDerivedStateFromError(self, _err: BaseException) -> object:  # noqa: N802
            return {"error": True}

        def componentDidCatch(self, _err: BaseException) -> None:  # noqa: N802
            # In upstream, setState in componentDidCatch synchronously affects the
            # subsequent recovery render. Our simplified model doesn't fully rebase
            # the update queue during this handled-error path, so mutate directly.
            self._state["error"] = True  # type: ignore[attr-defined]

        def render(self) -> object:
            if bool(self.state.get("error")):
                return create_element("div", {"text": "fallback"})
            children = self.props.get("children")
            if isinstance(children, tuple):
                return children[0] if children else None
            return children

    class Boom(Component):
        def render(self) -> object:
            raise RuntimeError("boom")

    root = create_noop_root()
    with WarningCapture() as cap:
        root.render(create_element(Boundary, {"children": create_element(Boom)}))
    assert any("getderivedstatefromerror" in str(r.message).lower() for r in cap.records)


def test_warns_if_getsnapshotbeforeupdate_is_static() -> None:
    # Upstream: ReactES6Class-test.js
    # "warns if getSnapshotBeforeUpdate is static"
    set_dev(True)

    class Bad(Component):
        @staticmethod
        def getSnapshotBeforeUpdate() -> object:  # noqa: N802
            return None

        def render(self) -> object:
            return create_element("div")

    root = create_noop_root()
    with WarningCapture() as cap:
        root.render(create_element(Bad))
    assert any("getsnapshotbeforeupdate" in str(r.message).lower() for r in cap.records)


def test_warns_if_state_not_initialized_before_static_getderivedstatefromprops() -> None:
    # Upstream: ReactES6Class-test.js
    # "warns if state not initialized before static getDerivedStateFromProps"
    set_dev(True)

    class Bad(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = None  # type: ignore[assignment]

        @staticmethod
        def getDerivedStateFromProps(_props: object, _state: object) -> object:  # noqa: N802
            return {"x": 1}

        def render(self) -> object:
            return create_element("div")

    root = create_noop_root()
    with WarningCapture() as cap:
        root.render(create_element(Bad))
    assert any(
        ("state must be initialized" in str(r.message).lower()) or ("initial state" in str(r.message).lower())
        for r in cap.records
    )


def test_throws_if_no_render_function_is_defined() -> None:
    # Upstream: ReactES6Class-test.js
    # "throws if no render function is defined"
    #
    # Python analogue: Component is abstract without a `render()` implementation.
    class MissingRender(Component):
        pass

    root = create_noop_root()
    try:
        root.render(create_element(MissingRender))
        raise AssertionError("expected render to throw")
    except TypeError as err:
        assert "render" in str(err).lower()


def test_should_warn_when_misspelling_componentwillreceiveprops() -> None:
    # Upstream: ReactES6Class-test.js
    # "should warn when misspelling componentWillReceiveProps"
    set_dev(True)

    class Bad(Component):
        def componentWillRecieveProps(self) -> None:  # noqa: N802
            pass

        def render(self) -> object:
            return create_element("div")

    root = create_noop_root()
    with WarningCapture() as cap:
        root.render(create_element(Bad))
    assert any("componentwillreceiveprops" in str(r.message).lower() for r in cap.records)


def test_should_warn_when_misspelling_shouldcomponentupdate() -> None:
    # Upstream: ReactES6Class-test.js
    # "should warn when misspelling shouldComponentUpdate"
    set_dev(True)

    class Bad(Component):
        def shouldComponentUpdatee(self) -> bool:  # noqa: N802
            return True

        def render(self) -> object:
            return create_element("div")

    root = create_noop_root()
    with WarningCapture() as cap:
        root.render(create_element(Bad))
    assert any("shouldcomponentupdate" in str(r.message).lower() for r in cap.records)


def test_should_warn_when_misspelling_unsafe_componentwillreceiveprops() -> None:
    # Upstream: ReactES6Class-test.js
    # "should warn when misspelling UNSAFE_componentWillReceiveProps"
    set_dev(True)

    class Bad(Component):
        def UNSAFE_componentWillRecieveProps(self) -> None:  # noqa: N802
            pass

        def render(self) -> object:
            return create_element("div")

    root = create_noop_root()
    with WarningCapture() as cap:
        root.render(create_element(Bad))
    assert any("unsafe_componentwillreceiveprops" in str(r.message).lower() for r in cap.records)


def test_should_render_with_null_in_the_initial_state_property() -> None:
    # Upstream: ReactES6Class-test.js
    # "should render with null in the initial state property"
    set_dev(True)

    class NullState(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = None  # type: ignore[assignment]

        def render(self) -> object:
            return create_element("div", {"ok": True})

    root = create_noop_root()
    with WarningCapture() as cap:
        root.render(create_element(NullState))
    assert not cap.records
    assert root.container.last_committed["props"]["ok"] is True
