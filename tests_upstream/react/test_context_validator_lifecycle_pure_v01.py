from __future__ import annotations

from typing import Any

from ryact import Component, PureComponent, create_context, create_element, create_ref
from ryact.context import Context, context_provider
from ryact.dev import set_dev
from ryact_testkit import WarningCapture, create_noop_root


def test_should_filter_out_context_not_in_contexttypes() -> None:
    # Upstream: ReactContextValidator-test.js — legacy merged context is filtered by contextTypes.
    child_ref = create_ref()

    class Leaf(Component):
        contextTypes = {"foo": object()}

        def render(self) -> object:
            return create_element("div")

    class Provider(Component):
        childContextTypes = {"foo": object(), "bar": object()}

        def getChildContext(self) -> dict[str, Any]:  # noqa: N802
            return {"foo": "abc", "bar": 123}

        def render(self) -> object:
            return create_element(Leaf, {"ref": child_ref})

    root = create_noop_root()
    root.render(create_element(Provider))
    root.flush()
    leaf_inst = child_ref.current
    assert isinstance(leaf_inst, Component)
    assert leaf_inst.context == {"foo": "abc"}


def test_should_pass_next_context_to_lifecycles() -> None:
    # Upstream: ReactContextValidator-test.js — legacy context in class lifecycles.
    constructor_context: dict[str, Any] | None = None
    render_context: dict[str, Any] | None = None
    cdm_context: dict[str, Any] | None = None
    cdu_context: dict[str, Any] | None = None
    cwrp_ctx: dict[str, Any] | None = None
    cwrp_next: dict[str, Any] | None = None
    scu_ctx: dict[str, Any] | None = None
    scu_next: dict[str, Any] | None = None
    cwum_ctx: dict[str, Any] | None = None
    cwum_next: dict[str, Any] | None = None

    class Parent(Component):
        childContextTypes = {"foo": object(), "bar": object()}

        def getChildContext(self) -> dict[str, Any]:  # noqa: N802
            return {"foo": self.props["foo"], "bar": "bar"}

        def render(self) -> object:
            return create_element(Child)

    class Child(Component):
        contextTypes = {"foo": object()}

        def __init__(self, **props: Any) -> None:
            super().__init__(**props)
            nonlocal constructor_context
            constructor_context = dict(self.context)

        def UNSAFE_componentWillReceiveProps(self, _next_props: Any, next_context: Any) -> None:  # noqa: N802
            nonlocal cwrp_ctx, cwrp_next
            cwrp_ctx = dict(self.context)
            cwrp_next = dict(next_context)

        def shouldComponentUpdate(self, next_props: Any, next_state: Any, next_context: Any) -> bool:  # noqa: N802
            nonlocal scu_ctx, scu_next
            scu_ctx = dict(self.context)
            scu_next = dict(next_context)
            return True

        def UNSAFE_componentWillUpdate(self, _np: Any, _ns: Any, next_context: Any) -> None:  # noqa: N802
            nonlocal cwum_ctx, cwum_next
            cwum_ctx = dict(self.context)
            cwum_next = dict(next_context)

        def render(self) -> object:
            nonlocal render_context
            render_context = dict(self.context)
            return create_element("div")

        def componentDidMount(self) -> None:  # noqa: N802
            nonlocal cdm_context
            cdm_context = dict(self.context)

        def componentDidUpdate(self) -> None:  # noqa: N802
            nonlocal cdu_context
            cdu_context = dict(self.context)

    root = create_noop_root()
    root.render(create_element(Parent, {"foo": "abc"}))
    root.flush()
    assert constructor_context == {"foo": "abc"}
    assert render_context == {"foo": "abc"}
    assert cdm_context == {"foo": "abc"}

    root.render(create_element(Parent, {"foo": "def"}))
    root.flush()

    assert cwrp_ctx == {"foo": "abc"}
    assert cwrp_next == {"foo": "def"}
    assert scu_ctx == {"foo": "abc"}
    assert scu_next == {"foo": "def"}
    assert cwum_ctx == {"foo": "abc"}
    assert cwum_next == {"foo": "def"}
    assert render_context == {"foo": "def"}
    assert cdu_context == {"foo": "def"}


def test_should_pass_parent_context_if_getchildcontext_method_is_missing() -> None:
    # Upstream: ReactContextValidator-test.js — middle legacy provider without getChildContext.
    set_dev(True)
    captured: dict[str, Any] = {}

    class ParentContextProvider(Component):
        childContextTypes = {"foo": object()}

        def getChildContext(self) -> dict[str, Any]:  # noqa: N802
            return {"foo": "FOO"}

        def render(self) -> object:
            return create_element(MiddleMissingContext)

    class MiddleMissingContext(Component):
        childContextTypes = {"bar": object()}

        def render(self) -> object:
            return create_element(ChildContextConsumer)

    class ChildContextConsumer(Component):
        contextTypes = {"bar": object(), "foo": object()}

        def render(self) -> object:
            captured.clear()
            captured.update(dict(self.context))
            return create_element("div")

    root = create_noop_root()
    with WarningCapture() as cap:
        root.render(create_element(ParentContextProvider))
        root.flush()
    assert any("getchildcontext" in str(r.message).lower() for r in cap.records)
    assert captured.get("bar") is None
    assert captured.get("foo") == "FOO"


def test_should_pass_next_context_to_lifecycles_on_update() -> None:
    # Upstream: ReactContextValidator-test.js — modern contextType + Provider value updates.
    first_context = {"foo": 123}
    second_context = {"bar": 456}
    Ctx: Context[Any] = create_context(None)

    constructor_ctx: Any = None
    render_ctx: Any = None
    cdm_ctx: Any = None
    cdu_ctx: Any = None
    cwrp_prev: Any = None
    cwrp_next: Any = None
    cwum_prev: Any = None
    cwum_next: Any = None
    scu_called = False

    class Inner(Component):
        contextType = Ctx

        def __init__(self, **props: Any) -> None:
            super().__init__(**props)
            nonlocal constructor_ctx
            constructor_ctx = self.context

        def UNSAFE_componentWillReceiveProps(self, _np: Any, next_context: Any) -> None:  # noqa: N802
            nonlocal cwrp_prev, cwrp_next
            cwrp_prev = self.context
            cwrp_next = next_context

        def shouldComponentUpdate(self, _np: Any, _ns: Any) -> bool:  # noqa: N802
            nonlocal scu_called
            scu_called = True
            return True

        def UNSAFE_componentWillUpdate(self, _np: Any, _ns: Any, next_context: Any) -> None:  # noqa: N802
            nonlocal cwum_prev, cwum_next
            cwum_prev = self.context
            cwum_next = next_context

        def render(self) -> object:
            nonlocal render_ctx
            render_ctx = self.context
            return create_element("div")

        def componentDidMount(self) -> None:  # noqa: N802
            nonlocal cdm_ctx
            cdm_ctx = self.context

        def componentDidUpdate(self) -> None:  # noqa: N802
            nonlocal cdu_ctx
            cdu_ctx = self.context

    root = create_noop_root()
    root.render(context_provider(Ctx, first_context, create_element(Inner)))
    root.flush()
    assert constructor_ctx is first_context
    assert render_ctx is first_context
    assert cdm_ctx is first_context

    root.render(context_provider(Ctx, second_context, create_element(Inner)))
    root.flush()

    assert cwrp_prev is first_context
    assert cwrp_next is second_context
    assert cwum_prev is first_context
    assert cwum_next is second_context
    assert render_ctx is second_context
    assert cdu_ctx is second_context
    assert scu_called is True


def test_should_rerender_purecomponents_when_context_provider_updates() -> None:
    # Upstream: ReactContextValidator-test.js — PureComponent respects context changes.
    Ctx: Context[Any] = create_context({"placeholder": True})
    seen: list[Any] = []

    class App(PureComponent):
        contextType = Ctx

        def render(self) -> object:
            seen.append(self.context)
            return create_element("div")

    first = {"foo": 123}
    second = {"bar": 456}
    root = create_noop_root()
    root.render(context_provider(Ctx, first, create_element(App)))
    root.flush()
    assert seen[-1] is first
    root.render(context_provider(Ctx, second, create_element(App)))
    root.flush()
    assert seen[-1] is second
