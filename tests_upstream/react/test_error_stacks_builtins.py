from __future__ import annotations

import re

import pytest
from ryact import create_element
from ryact.concurrent import Suspend, Thenable, activity, lazy, suspense
from ryact_testkit import create_noop_root


def test_includes_built_in_for_activity() -> None:
    # Upstream: ReactErrorStacks-test.js — "includes built-in for Activity"
    def Boom(**_: object) -> object:
        raise RuntimeError("boom")

    root = create_noop_root()
    with pytest.raises(RuntimeError, match=re.escape("boom")) as exc:
        root.render(activity(children=create_element(Boom)))

    msg = str(exc.value)
    assert "Component stack:" in msg
    assert "in Activity" in msg


def test_includes_built_in_for_suspense() -> None:
    # Upstream: ReactErrorStacks-test.js — "includes built-in for Suspense"
    def Boom(**_: object) -> object:
        raise RuntimeError("boom")

    root = create_noop_root()
    with pytest.raises(RuntimeError, match=re.escape("boom")) as exc:
        root.render(suspense(fallback=None, children=create_element(Boom)))

    msg = str(exc.value)
    assert "Component stack:" in msg
    assert "in Suspense" in msg


def test_includes_built_in_for_suspense_fallbacks() -> None:
    # Upstream: ReactErrorStacks-test.js — "includes built-in for Suspense fallbacks"
    thenable = Thenable()

    def Suspender(**_: object) -> object:
        raise Suspend(thenable)

    def Boom(**_: object) -> object:
        raise RuntimeError("boom")

    root = create_noop_root()
    with pytest.raises(RuntimeError, match=re.escape("boom")) as exc:
        root.render(
            suspense(
                fallback=create_element(Boom),
                children=create_element(Suspender),
            )
        )

    msg = str(exc.value)
    assert "Component stack:" in msg
    assert "in Suspense" in msg


def test_includes_built_in_for_lazy() -> None:
    # Upstream: ReactErrorStacks-test.js — "includes built-in for Lazy"
    def Boom(**_: object) -> object:
        raise RuntimeError("boom")

    LazyBoom = lazy(lambda: Boom)

    root = create_noop_root()
    with pytest.raises(RuntimeError, match=re.escape("boom")) as exc:
        root.render(create_element(LazyBoom))

    msg = str(exc.value)
    assert "Component stack:" in msg
    assert "in Lazy" in msg
