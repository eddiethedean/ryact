from __future__ import annotations

from typing import Any

import pytest
from ryact import Component, create_context, create_element, forward_ref, fragment
from ryact.concurrent import (
    Fragment,
    Offscreen,
    Portal,
    Profiler,
    StrictMode,
    SuspenseList,
    Thenable,
    TracingMarker,
    ViewTransition,
    lazy,
)
from ryact_testkit import create_noop_root


def _span(text: str) -> Any:
    return create_element("span", {"text": text})


def test_throws_when_wrapping_fragment() -> None:
    # Upstream: ReactLazy-test.internal.js — "throws with a useful error when wrapping Fragment with lazy()"
    Bad = lazy(lambda: {"default": Fragment})
    root = create_noop_root()
    with pytest.raises(TypeError, match="forbidden internal component"):
        root.render(create_element(Bad))


def test_throws_when_wrapping_strict_mode() -> None:
    Bad = lazy(lambda: {"default": StrictMode})
    root = create_noop_root()
    with pytest.raises(TypeError, match="forbidden internal component"):
        root.render(create_element(Bad))


def test_throws_when_wrapping_profiler() -> None:
    Bad = lazy(lambda: {"default": Profiler})
    root = create_noop_root()
    with pytest.raises(TypeError, match="forbidden internal component"):
        root.render(create_element(Bad))


def test_throws_when_wrapping_create_portal_with_lazy() -> None:
    # Upstream: "throws with a useful error when wrapping createPortal with lazy()"
    Bad = lazy(lambda: {"default": Portal})
    root = create_noop_root()
    with pytest.raises(TypeError, match="forbidden internal component"):
        root.render(create_element(Bad))


def test_throws_when_wrapping_suspense_boundary_token() -> None:
    Bad = lazy(lambda: {"default": "__suspense__"})
    root = create_noop_root()
    with pytest.raises(TypeError, match="forbidden internal component"):
        root.render(create_element(Bad))


def test_throws_when_wrapping_suspense_list() -> None:
    Bad = lazy(lambda: {"default": SuspenseList})
    root = create_noop_root()
    with pytest.raises(TypeError, match="forbidden internal component"):
        root.render(create_element(Bad))


def test_throws_when_wrapping_activity() -> None:
    Bad = lazy(lambda: {"default": Offscreen})
    root = create_noop_root()
    with pytest.raises(TypeError, match="forbidden internal component"):
        root.render(create_element(Bad))


def test_throws_when_wrapping_tracing_marker() -> None:
    Bad = lazy(lambda: {"default": TracingMarker})
    root = create_noop_root()
    with pytest.raises(TypeError, match="forbidden internal component"):
        root.render(create_element(Bad))


def test_throws_when_wrapping_view_transition() -> None:
    Bad = lazy(lambda: {"default": ViewTransition})
    root = create_noop_root()
    with pytest.raises(TypeError, match="forbidden internal component"):
        root.render(create_element(Bad))


def test_throws_when_wrapping_context_consumer() -> None:
    ctx = create_context(0)
    Bad = lazy(lambda: {"default": ctx.Consumer})
    root = create_noop_root()
    with pytest.raises(TypeError, match="Context.Consumer"):
        root.render(create_element(Bad))


def test_throws_when_wrapping_invalid_type() -> None:
    Bad = lazy(lambda: {"default": object()})
    root = create_noop_root()
    with pytest.raises(TypeError, match="lazy\\(\\) default export"):
        root.render(create_element(Bad))


def test_throws_when_wrapping_lazy_multiple_times() -> None:
    Inner = lazy(lambda: {"default": lambda: _span("in")})
    Bad = lazy(lambda: {"default": Inner})
    root = create_noop_root()
    with pytest.raises(TypeError, match="nested lazy"):
        root.render(create_element(Bad))


def test_does_not_support_arbitrary_promises_only_module_objects() -> None:
    # Upstream: "does not support arbitrary promises, only module objects"
    root = create_noop_root()
    Bad_sync = lazy(lambda: {})
    with pytest.raises(TypeError, match="default"):
        root.render(create_element(Bad_sync))

    t: Thenable = Thenable()

    def loader() -> Thenable:
        t.resolve({})
        return t

    Bad_async = lazy(loader)
    root2 = create_noop_root()
    with pytest.raises(TypeError, match="default"):
        root2.render(create_element(Bad_async))


def test_supports_class_and_forward_ref_components() -> None:
    # Upstream: "supports class and forwardRef components"

    class Inner(Component):
        def render(self) -> Any:
            return _span("cls")

    LazyCls = lazy(lambda: {"default": Inner})

    Fr = forward_ref(lambda props, ref: _span("fr"))
    LazyFr = lazy(lambda: {"default": Fr})

    root = create_noop_root()
    root.render(fragment(create_element(LazyCls), create_element(LazyFr)))
    assert root.container.last_committed is not None


def test_multiple_lazy_components() -> None:
    # Upstream: "multiple lazy components"
    def A() -> Any:
        return _span("a")

    def B() -> Any:
        return _span("b")

    LA = lazy(lambda: {"default": A})
    LB = lazy(lambda: {"default": B})

    root = create_noop_root()
    root.render(fragment(create_element(LA), create_element(LB)))
    snap = root.container.last_committed
    assert snap is not None
