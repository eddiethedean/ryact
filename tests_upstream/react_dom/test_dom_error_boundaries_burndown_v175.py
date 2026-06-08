# Translated from: packages/react-dom/src/__tests__/ReactErrorBoundaries-test.internal.js
# Burndown v175: createRoot effects, cWU recovery, refs, reorders, gsbu, GDSFE.
from __future__ import annotations

import random
from collections.abc import Iterator
from typing import Any

import pytest
from ryact import Component, Fragment, create_element, create_ref, use_effect, use_layout_effect
from ryact.dev import is_dev, set_dev
from ryact_dom.dom import Container, ElementNode
from ryact_dom.dom_internals import reset_component_dom_registry
from ryact_dom.error_reporting import console_error_log
from ryact_dom.root import Root, create_root
from ryact_testkit import WarningCapture, act, set_act_environment_enabled


@pytest.fixture(autouse=True)
def _dev_and_act() -> Iterator[None]:
    prev = is_dev()
    set_dev(True)
    set_act_environment_enabled(True)
    reset_component_dom_registry()
    yield
    reset_component_dom_registry()
    set_dev(prev)


def _text(c: Container) -> str:
    return c.text_content


def _console_strs(c: Container) -> list[str]:
    out: list[str] = []
    for item in console_error_log(c):
        if isinstance(item, BaseException):
            out.append(str(item))
        elif isinstance(item, str):
            out.append(item)
        elif isinstance(item, tuple):
            out.extend(str(x) for x in item)
    return out


def _aggregate_errors(err: BaseException) -> list[BaseException]:
    errors = getattr(err, "errors", None)
    if errors is not None:
        return list(errors)
    if hasattr(err, "exceptions"):
        return list(err.exceptions)
    return [err]


def _render(container: Container, element: object) -> Root:
    root = create_root(container)
    with act(flush=root.flush_sync):
        root.render(element)
    return root


def _update(root: Root, element: object) -> None:
    with act(flush=root.flush_sync):
        root.render(element)


class BrokenRender(Component):
    def render(self) -> object:
        raise RuntimeError("Hello")


class BrokenComponentDidMount(Component):
    def componentDidMount(self) -> None:  # noqa: N802
        raise RuntimeError(str(self.props.get("msg", "Hello")))

    def render(self) -> object:
        return create_element("span", None, "x")


class BrokenComponentWillUnmount(Component):
    def componentWillUnmount(self) -> None:  # noqa: N802
        raise RuntimeError("Hello")

    def render(self) -> object:
        return create_element("span", None, "x")


class BrokenComponentWillMountWithContext(Component):
    childContextTypes = {"foo": object}  # type: ignore[attr-defined]

    def getChildContext(self) -> dict[str, int]:  # noqa: N802
        return {"foo": 42}

    def UNSAFE_componentWillMount(self) -> None:  # noqa: N802
        raise RuntimeError("Hello")

    def render(self) -> object:
        return self.props.get("children")


class ErrorBoundary(Component):
    def __init__(self, **props: object) -> None:
        super().__init__(**props)
        self._state: dict[str, Any] = {"error": None}
        self._did_catch_errors: list[str] = []

    def componentDidCatch(self, error: BaseException) -> None:  # noqa: N802
        self._did_catch_errors.append(str(error))
        self.set_state({"error": error})

    def render(self) -> object:
        err = self.state.get("error")
        if err is not None and not self.props.get("forceRetry"):
            ref = self.props.get("errorMessageRef")
            return create_element("span", {"ref": ref}, f"Caught an error: {err}.")
        children = self.props.get("children")
        if isinstance(children, tuple):
            return create_element(Fragment, None, *children)
        return children


class GDSFEOnlyBoundary(Component):
    _gdsfe_errors: list[str] = []

    def __init__(self, **props: object) -> None:
        super().__init__(**props)
        self._state: dict[str, Any] = {"error": None}

    @classmethod
    def getDerivedStateFromError(cls, error: BaseException) -> dict[str, Any]:  # noqa: N802
        cls._gdsfe_errors.append(str(error))
        return {"error": error}

    def render(self) -> object:
        err = self.state.get("error")
        if err is not None and not self.props.get("forceRetry"):
            return create_element("span", None, f"Caught an error: {err}.")
        children = self.props.get("children")
        if isinstance(children, tuple):
            return create_element(Fragment, None, *children)
        return children


class BothHooksBoundary(Component):
    did_catch_called = False
    gdsfe_called = False

    def __init__(self, **props: object) -> None:
        super().__init__(**props)
        self._state: dict[str, Any] = {"error": None}

    @staticmethod
    def getDerivedStateFromError(error: BaseException) -> dict[str, Any]:  # noqa: N802
        BothHooksBoundary.gdsfe_called = True
        return {"error": error}

    def componentDidCatch(self, error: BaseException) -> None:  # noqa: N802
        BothHooksBoundary.did_catch_called = True
        self.set_state({"error": error})

    def render(self) -> object:
        err = self.state.get("error")
        if err is not None:
            return create_element("span", None, f"Caught an error: {err}.")
        return self.props.get("children")


class DidCatchOnlyNoStateBoundary(Component):
    def componentDidCatch(self, _error: BaseException) -> None:  # noqa: N802
        pass

    def render(self) -> object:
        return self.props.get("children")


_fail_reorder_render = False


class MaybeBrokenRender(Component):
    def render(self) -> object:
        if _fail_reorder_render:
            raise RuntimeError("Hello")
        return create_element("div", None, self.props.get("children"))


class Normal(Component):
    def render(self) -> object:
        return create_element("span", None, "N")


def _shuffled_error_boundary_children() -> tuple[object, ...]:
    elements: list[object] = [create_element(Normal, {"key": str(i)}) for i in range(20)]
    elements.append(create_element(MaybeBrokenRender, {"key": "broken"}))
    random.shuffle(elements)
    return tuple(elements)


def test_catches_errors_in_useeffect() -> None:
    def BrokenEffect(**_props: object) -> object:
        def eff() -> None:
            raise RuntimeError("Hello")

        use_effect(eff, ())
        return create_element("span", None, "x")

    c = Container()
    _render(c, create_element(ErrorBoundary, None, create_element(BrokenEffect)))
    assert _text(c) == "Caught an error: Hello."


def test_catches_errors_in_uselayouteffect() -> None:
    def BrokenLayout(**_props: object) -> object:
        def eff() -> None:
            raise RuntimeError("Hello")

        use_layout_effect(eff, ())
        return create_element("span", None, "x")

    c = Container()
    _render(c, create_element(ErrorBoundary, None, create_element(BrokenLayout)))
    assert _text(c) == "Caught an error: Hello."


def test_catches_errors_thrown_in_componentwillunmount() -> None:
    c = Container()
    root = _render(
        c,
        create_element(
            ErrorBoundary,
            {"key": "eb"},
            create_element(BrokenComponentWillUnmount, {"key": "broken"}),
        ),
    )
    _update(root, create_element(ErrorBoundary, {"key": "eb"}))
    assert _text(c) == "Caught an error: Hello."


def test_recovers_from_componentwillunmount_errors_on_update() -> None:
    c = Container()
    root = _render(
        c,
        create_element(
            ErrorBoundary,
            {"key": "eb"},
            create_element(BrokenComponentWillUnmount, {"key": "broken"}),
        ),
    )
    _update(root, create_element(ErrorBoundary, {"key": "eb"}))
    assert _text(c) == "Caught an error: Hello."


def test_recovers_from_nested_componentwillunmount_errors_on_update() -> None:
    c = Container()
    root = _render(
        c,
        create_element(
            ErrorBoundary,
            {"key": "outer", "name": "Outer"},
            create_element(
                ErrorBoundary,
                {"key": "inner", "name": "Inner"},
                create_element(BrokenComponentWillUnmount, {"key": "broken"}),
            ),
        ),
    )
    _update(
        root,
        create_element(
            ErrorBoundary,
            {"key": "outer", "name": "Outer"},
            create_element(ErrorBoundary, {"key": "inner", "name": "Inner"}),
        ),
    )
    assert _text(c) == "Caught an error: Hello."


def test_keeps_refs_up_to_date_during_updates() -> None:
    ops: list[ElementNode | None] = []

    def child_ref(node: ElementNode | None) -> None:
        ops.append(node)

    c = Container()
    root = _render(
        c,
        create_element(ErrorBoundary, {"key": "eb"}, create_element("div", {"key": "d", "ref": child_ref})),
    )
    assert len(ops) == 1
    assert isinstance(ops[0], ElementNode)

    _update(
        root,
        create_element(
            ErrorBoundary,
            {"key": "eb"},
            create_element("div", {"key": "d", "ref": child_ref}),
            create_element(BrokenRender, {"key": "broken"}),
        ),
    )
    assert ops[-2:] == [ops[0], None]
    assert _text(c) == "Caught an error: Hello."


def test_resets_callback_refs_if_mounting_aborts() -> None:
    ops: list[tuple[str, ElementNode | None]] = []

    def child_ref(node: ElementNode | None) -> None:
        ops.append(("child", node))

    error_ref = create_ref()
    c = Container()
    _render(
        c,
        create_element(
            ErrorBoundary,
            {"key": "eb", "errorMessageRef": error_ref},
            create_element("div", {"key": "d", "ref": child_ref}),
            create_element(BrokenRender, {"key": "broken"}),
        ),
    )
    assert ops == []
    assert isinstance(error_ref.current, ElementNode)
    assert _text(c) == "Caught an error: Hello."


def test_picks_the_right_boundary_when_handling_unmounting_errors() -> None:
    c = Container()
    root = _render(
        c,
        create_element(
            ErrorBoundary,
            {"key": "outer", "name": "Outer"},
            create_element(
                ErrorBoundary,
                {"key": "inner", "name": "Inner"},
                create_element(BrokenComponentWillUnmount, {"key": "broken"}),
            ),
        ),
    )
    _update(
        root,
        create_element(
            ErrorBoundary,
            {"key": "outer", "name": "Outer"},
            create_element(ErrorBoundary, {"key": "inner", "name": "Inner"}),
        ),
    )
    outer = c._ryact_dom_root._class_instances[(ErrorBoundary, "outer")]
    inner = c._ryact_dom_root._class_instances[(ErrorBoundary, "inner")]
    assert outer.state.get("error") is None
    assert inner.state.get("error") is not None
    assert _text(c) == "Caught an error: Hello."


def test_doesnt_get_into_inconsistent_state_during_reorders() -> None:
    global _fail_reorder_render
    c = Container()
    _fail_reorder_render = False
    root = _render(c, create_element(ErrorBoundary, {"key": "eb"}, *_shuffled_error_boundary_children()))
    assert "Caught an error" not in _text(c)

    _fail_reorder_render = True
    _update(root, create_element(ErrorBoundary, {"key": "eb"}, *_shuffled_error_boundary_children()))
    assert _text(c) == "Caught an error: Hello."


def test_renders_an_error_state_if_context_provider_throws_in_componentwillmount() -> None:
    c = Container()
    with WarningCapture() as cap:
        _render(
            c,
            create_element(
                ErrorBoundary,
                {"key": "eb"},
                create_element(
                    BrokenComponentWillMountWithContext,
                    {"key": "broken"},
                    create_element("span", None, "x"),
                ),
            ),
        )
    assert _text(c) == "Caught an error: Hello."
    assert any("childContextTypes" in str(r.message) for r in cap.records)


def test_handles_errors_that_occur_in_before_mutation_commit_hook() -> None:
    errors_log: list[str] = []

    class Parent(Component):
        def getSnapshotBeforeUpdate(self, *_args: object) -> None:  # noqa: N802
            errors_log.append("parent sad")
            raise RuntimeError("parent sad")

        def componentDidUpdate(self, *_args: object) -> None:  # noqa: N802
            pass

        def render(self) -> object:
            return create_element(Child, {"n": self.props.get("n")})

    class Child(Component):
        def getSnapshotBeforeUpdate(self, *_args: object) -> None:  # noqa: N802
            errors_log.append("child sad")
            raise RuntimeError("child sad")

        def componentDidUpdate(self, *_args: object) -> None:  # noqa: N802
            pass

        def render(self) -> object:
            return create_element("span", None, str(self.props.get("n")))

    c = Container()
    root = _render(c, create_element(Parent, {"n": 0}))
    with pytest.raises(BaseException) as excinfo:
        _update(root, create_element(Parent, {"n": 1}))
    caught = _aggregate_errors(excinfo.value)
    assert [str(e) for e in caught] == ["child sad", "parent sad"]
    assert errors_log == ["child sad", "parent sad"]


def test_passes_an_aggregate_error_when_two_errors_happen_in_commit() -> None:
    c = Container()
    with pytest.raises(BaseException) as excinfo:
        _render(
            c,
            create_element(
                Fragment,
                None,
                create_element(BrokenComponentDidMount, {"key": "a", "msg": "A"}),
                create_element(BrokenComponentDidMount, {"key": "b", "msg": "B"}),
            ),
        )
    caught = _aggregate_errors(excinfo.value)
    assert [str(e) for e in caught] == ["A", "B"]


def test_calls_static_getderivedstatefromerror_for_each_error_that_is_captured() -> None:
    GDSFEOnlyBoundary._gdsfe_errors = []
    c = Container()
    _render(
        c,
        create_element(
            GDSFEOnlyBoundary,
            {"key": "eb"},
            create_element(BrokenRender, {"key": "broken"}),
        ),
    )
    assert _text(c) == "Caught an error: Hello."
    assert GDSFEOnlyBoundary._gdsfe_errors == ["Hello"]

    c2 = Container()
    _render(
        c2,
        create_element(
            GDSFEOnlyBoundary,
            {"key": "eb2"},
            create_element(BrokenRender, {"key": "broken2"}),
        ),
    )
    assert GDSFEOnlyBoundary._gdsfe_errors == ["Hello", "Hello"]


def test_catches_errors_thrown_while_detaching_refs() -> None:
    def BrokenDetach(**_props: object) -> object:
        def ref(node: ElementNode | None) -> object | None:
            if node is not None:

                def cleanup() -> None:
                    raise RuntimeError("Hello")

                return cleanup
            return None

        return create_element("span", {"ref": ref}, "x")

    c = Container()
    root = _render(c, create_element(ErrorBoundary, None, create_element(BrokenDetach, {"key": "b"})))
    _update(root, create_element(ErrorBoundary, None))
    assert _text(c) == "Caught an error: Hello."


def test_should_call_both_componentdidcatch_and_getderivedstatefromerror_if_both_exist() -> None:
    BothHooksBoundary.did_catch_called = False
    BothHooksBoundary.gdsfe_called = False
    c = Container()
    _render(c, create_element(BothHooksBoundary, None, create_element(BrokenRender)))
    assert _text(c) == "Caught an error: Hello."
    assert BothHooksBoundary.gdsfe_called is True
    assert BothHooksBoundary.did_catch_called is True


def test_should_warn_if_an_error_boundary_with_only_componentdidcatch_does_not_update_state() -> None:
    c = Container()
    _render(
        c,
        create_element(
            "div",
            None,
            "Sibling",
            create_element(DidCatchOnlyNoStateBoundary, None, create_element(BrokenRender)),
        ),
    )
    msgs = _console_strs(c)
    assert _text(c) == "Sibling"
    assert any(
        "DidCatchOnlyNoStateBoundary: Error boundaries should implement getDerivedStateFromError()" in m for m in msgs
    )
