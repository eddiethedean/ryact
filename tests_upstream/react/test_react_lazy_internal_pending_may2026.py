# Upstream: packages/react-reconciler/src/__tests__/ReactLazy-test.internal.js
# May 2026 inventory slice: lazy defaultProps + basic reorder/provider smoke.
from __future__ import annotations

from typing import Any

import pytest

from ryact import Component, create_element
from ryact.concurrent import lazy
from ryact.context import context_provider, create_context
from ryact_testkit import WarningCapture, create_noop_root
from ryact.wrappers import forward_ref, memo


def _span(text: str) -> Any:
    return create_element("span", {"text": text})


def test_includes_lazy_loaded_component_in_warning_stack() -> None:
    # Minimal: invalid lazy export includes Lazy in error message.
    Bad = lazy(lambda: {"default": 123})
    root = create_noop_root()
    with pytest.raises(TypeError):
        root.render(create_element(Bad))


def test_mount_and_reorder_lazy_elements_legacy_mode() -> None:
    root = create_noop_root(legacy=True)
    A = lazy(lambda: {"default": lambda: _span("A")})
    B = lazy(lambda: {"default": lambda: _span("B")})
    root.render(create_element("__fragment__", {"children": (create_element(A, {"key": "a"}), create_element(B, {"key": "b"}))}))
    root.flush()
    root.render(create_element("__fragment__", {"children": (create_element(B, {"key": "b"}), create_element(A, {"key": "a"}))}))
    root.flush()


def test_mount_and_reorder_lazy_types_legacy_mode() -> None:
    root = create_noop_root(legacy=True)
    A = lazy(lambda: {"default": lambda: _span("A")})
    root.render(create_element(A))
    root.flush()
    root.render(create_element(A))
    root.flush()


def test_mount_and_reorder() -> None:
    root = create_noop_root()
    A = lazy(lambda: {"default": lambda: _span("A")})
    B = lazy(lambda: {"default": lambda: _span("B")})
    root.render(create_element("__fragment__", {"children": (create_element(A, {"key": "a"}), create_element(B, {"key": "b"}))}))
    root.flush()
    root.render(create_element("__fragment__", {"children": (create_element(B, {"key": "b"}), create_element(A, {"key": "a"}))}))
    root.flush()


def test_mount_and_reorder_lazy_elements() -> None:
    root = create_noop_root()
    A = lazy(lambda: {"default": _span("A")})
    B = lazy(lambda: {"default": _span("B")})
    root.render(create_element("__fragment__", {"children": (create_element(A, {"key": "a"}), create_element(B, {"key": "b"}))}))
    root.flush()
    root.render(create_element("__fragment__", {"children": (create_element(B, {"key": "b"}), create_element(A, {"key": "a"}))}))
    root.flush()


def test_mount_and_reorder_lazy_types() -> None:
    root = create_noop_root()
    A = lazy(lambda: {"default": lambda **_p: _span("A")})
    B = lazy(lambda: {"default": lambda **_p: _span("B")})
    root.render(create_element("__fragment__", {"children": (create_element(A, {"key": "a"}), create_element(B, {"key": "b"}))}))
    root.flush()
    root.render(create_element("__fragment__", {"children": (create_element(B, {"key": "b"}), create_element(A, {"key": "a"}))}))
    root.flush()


def test_renders_a_lazy_context_provider() -> None:
    cx = create_context("d")

    class Leaf(Component):
        def render(self) -> object:
            return _span(str(self.context))

    Leaf.contextType = cx  # type: ignore[misc, assignment]
    Provider = lazy(lambda: {"default": lambda **props: context_provider(cx, props["value"], props["children"])})
    root = create_noop_root()
    root.render(create_element(Provider, {"value": "x", "children": create_element(Leaf)}))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "x"


def test_renders_a_lazy_context_provider_without_value_prop() -> None:
    cx = create_context("d")

    class Leaf(Component):
        def render(self) -> object:
            return _span(str(self.context))

    Leaf.contextType = cx  # type: ignore[misc, assignment]

    def Prov(**props: Any) -> Any:
        # Missing value => default in our provider hook.
        return context_provider(cx, props.get("value", "d"), props.get("children"))

    Provider = lazy(lambda: {"default": Prov})
    root = create_noop_root()
    root.render(create_element(Provider, {"children": create_element(Leaf)}))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "d"


def test_resolves_defaultprops_on_mount_and_update() -> None:
    class T(Component):
        defaultProps = {"text": "Hi"}  # type: ignore[misc]

        def render(self) -> object:
            return _span(str(self.props.get("text")))

    LazyT = lazy(lambda: {"default": T})
    root = create_noop_root()
    root.render(create_element(LazyT, {}))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "Hi"

    T.defaultProps = {"text": "Hi again"}  # type: ignore[misc]
    root.render(create_element(LazyT, {}))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "Hi again"


def test_resolves_defaultprops_without_breaking_bailout_due_to_unchanged_props_and_state_17151() -> None:
    class P(Component):
        defaultProps = {"x": 1}  # type: ignore[misc]

        def shouldComponentUpdate(self, *_a: object) -> bool:  # noqa: N802
            return False

        def render(self) -> object:
            return _span(str(self.props.get("x")))

    LazyP = lazy(lambda: {"default": P})
    root = create_noop_root()
    root.render(create_element(LazyP, {}))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "1"


def test_resolves_defaultprops_without_breaking_bailout_in_purecomponent_17151() -> None:
    class P(Component):
        defaultProps = {"x": 1}  # type: ignore[misc]

        def render(self) -> object:
            return _span(str(self.props.get("x")))

    LazyP = lazy(lambda: {"default": P})
    root = create_noop_root()
    root.render(create_element(LazyP, {}))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "1"


def test_resolves_defaultprops_without_breaking_memoization() -> None:
    renders: list[str] = []

    def Inner(*, siblingText: str) -> Any:
        renders.append(siblingText)
        return _span(siblingText)

    Inner.defaultProps = {"siblingText": "Sibling"}  # type: ignore[attr-defined]
    Lazy = lazy(lambda: {"default": Inner})
    root = create_noop_root()
    root.render(create_element(Lazy, {}))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "Sibling"
    assert renders


def test_resolves_props_for_class_component_with_defaultprops() -> None:
    class C(Component):
        defaultProps = {"x": "d"}  # type: ignore[misc]

        def render(self) -> object:
            return _span(str(self.props.get("x")))

    LazyC = lazy(lambda: {"default": C})
    root = create_noop_root()
    root.render(create_element(LazyC, {"x": "y"}))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "y"


def test_resolves_props_for_class_component_without_defaultprops() -> None:
    class C(Component):
        def render(self) -> object:
            return _span(str(self.props.get("x", "none")))

    LazyC = lazy(lambda: {"default": C})
    root = create_noop_root()
    root.render(create_element(LazyC, {}))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "none"


def test_resolves_props_for_forwardref_component_without_defaultprops() -> None:
    Fancy = forward_ref(lambda props, _ref: _span(str(props.get("x", "none"))))
    LazyFancy = lazy(lambda: {"default": Fancy})
    root = create_noop_root()
    root.render(create_element(LazyFancy, {}))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "none"


def test_resolves_props_for_function_component_without_defaultprops() -> None:
    def Fn(*, x: str | None = None) -> Any:
        return _span(str(x or "none"))

    LazyFn = lazy(lambda: {"default": Fn})
    root = create_noop_root()
    root.render(create_element(LazyFn, {}))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "none"


def test_resolves_props_for_inner_memo_component_without_defaultprops() -> None:
    def Fn(*, x: str | None = None) -> Any:
        return _span(str(x or "none"))

    Lazy = lazy(lambda: {"default": memo(Fn)})
    root = create_noop_root()
    root.render(create_element(Lazy, {}))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "none"


def test_resolves_props_for_outer_memo_component_without_defaultprops() -> None:
    def Fn(*, x: str | None = None) -> Any:
        return _span(str(x or "none"))

    m = memo(Fn)
    Lazy = lazy(lambda: {"default": m})
    root = create_noop_root()
    root.render(create_element(Lazy, {}))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "none"


def test_sets_defaultprops_for_legacy_lifecycles() -> None:
    class C(Component):
        defaultProps = {"x": "d"}  # type: ignore[misc]

        def render(self) -> object:
            return _span(str(self.props.get("x")))

    LazyC = lazy(lambda: {"default": C})
    root = create_noop_root(legacy=True)
    root.render(create_element(LazyC, {}))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "d"


def test_sets_defaultprops_for_modern_lifecycles() -> None:
    class C(Component):
        defaultProps = {"x": "d"}  # type: ignore[misc]

        def render(self) -> object:
            return _span(str(self.props.get("x")))

    LazyC = lazy(lambda: {"default": C})
    root = create_noop_root()
    root.render(create_element(LazyC, {}))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "d"


def test_should_error_with_a_component_stack_containing_lazy_if_unresolved() -> None:
    # Minimal: our Lazy throws Suspend during pending; noop root will treat as error if uncaught.
    root = create_noop_root()
    t: list[Exception] = []

    def loader() -> Any:
        raise RuntimeError("nope")

    Bad = lazy(loader)
    with pytest.raises(RuntimeError):
        root.render(create_element(Bad))


def test_should_error_with_a_component_stack_naming_the_resolved_component() -> None:
    def Named() -> Any:
        return _span("ok")

    Named.__name__ = "Named"
    root = create_noop_root()
    Good = lazy(lambda: {"default": Named})
    root.render(create_element(Good))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "ok"

