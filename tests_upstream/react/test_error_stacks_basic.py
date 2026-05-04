from __future__ import annotations

import re

import pytest
from ryact import create_element
from ryact_testkit import create_noop_root


def test_error_in_component_includes_component_stack() -> None:
    # Upstream: ReactErrorStacks-test.js
    # Minimal slice: errors should include a deterministic component stack.

    def Boom(**_: object) -> object:
        raise RuntimeError("boom")

    root = create_noop_root()
    with pytest.raises(RuntimeError, match=re.escape("boom")) as exc:
        root.render(create_element(Boom, None))

    msg = str(exc.value)
    assert "Component stack:" in msg
    assert "in Boom" in msg


def test_includes_built_in_for_activity() -> None:
    # Upstream: ReactErrorStacks-test.js
    # "includes built-in for Activity"
    from ryact.concurrent import activity

    def Boom(**_: object) -> object:
        raise RuntimeError("boom")

    root = create_noop_root()
    with pytest.raises(RuntimeError) as exc:
        root.render(activity(children=create_element(Boom)))
    assert "in Activity" in str(exc.value)


def test_includes_built_in_for_lazy() -> None:
    # Upstream: ReactErrorStacks-test.js
    # "includes built-in for Lazy"
    from ryact.concurrent import lazy

    def Boom(**_: object) -> object:
        raise RuntimeError("boom")

    LazyBoom = lazy(lambda: Boom)
    root = create_noop_root()
    with pytest.raises(RuntimeError) as exc:
        root.render(create_element(LazyBoom))
    assert "in Lazy" in str(exc.value)


def test_includes_built_in_for_suspense() -> None:
    # Upstream: ReactErrorStacks-test.js
    # "includes built-in for Suspense"
    from ryact.concurrent import Suspend, Thenable, suspense

    thenable = Thenable()

    def Suspender(**_: object) -> object:
        raise Suspend(thenable)

    def Boom(**_: object) -> object:
        raise RuntimeError("boom")

    root = create_noop_root()
    with pytest.raises(RuntimeError) as exc:
        root.render(
            suspense(
                fallback=create_element(Boom),
                children=create_element(Suspender),
            )
        )
    assert "in Suspense" in str(exc.value)


def test_includes_built_in_for_suspense_fallbacks() -> None:
    # Upstream: ReactErrorStacks-test.js
    # "includes built-in for Suspense fallbacks"
    from ryact.concurrent import Suspend, Thenable, suspense

    thenable = Thenable()

    def Suspender(**_: object) -> object:
        raise Suspend(thenable)

    def Boom(**_: object) -> object:
        raise RuntimeError("boom")

    root = create_noop_root()
    with pytest.raises(RuntimeError) as exc:
        root.render(
            suspense(
                fallback=create_element(Boom),
                children=create_element(Suspender),
            )
        )
    msg = str(exc.value)
    assert "in Suspense" in msg
