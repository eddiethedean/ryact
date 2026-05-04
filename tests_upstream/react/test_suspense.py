from __future__ import annotations

from ryact import create_element
from ryact.concurrent import Suspend, Thenable, suspense
from ryact_testkit import create_noop_root


def test_suspends_and_shows_fallback() -> None:
    # Upstream: ReactSuspenseFallback-test.js
    # "suspends and shows fallback"
    root = create_noop_root()

    thenable = Thenable()
    resolved = {"ok": False}

    def AsyncText() -> object:
        if not resolved["ok"]:
            raise Suspend(thenable)
        return create_element("span", {"text": "Done"})

    element = suspense(
        fallback=create_element("div", {"text": "Loading"}),
        children=create_element(AsyncText),
    )

    root.render(element)
    assert root.container.last_committed == {
        "type": "div",
        "key": None,
        "props": {"text": "Loading"},
        "children": [],
    }

    resolved["ok"] = True
    thenable.resolve()
    root.flush()
    assert root.container.last_committed == {
        "type": "span",
        "key": None,
        "props": {"text": "Done"},
        "children": [],
    }


def test_suspends_and_shows_null_fallback() -> None:
    # Upstream: ReactSuspenseFallback-test.js — "suspends and shows null fallback"
    root = create_noop_root()
    thenable = Thenable()
    resolved = {"ok": False}

    def AsyncText() -> object:
        if not resolved["ok"]:
            raise Suspend(thenable)
        return create_element("span", {"text": "Done"})

    root.render(suspense(fallback=None, children=create_element(AsyncText)))
    assert root.container.last_committed is None

    resolved["ok"] = True
    thenable.resolve()
    root.flush()
    assert root.container.last_committed == {
        "type": "span",
        "key": None,
        "props": {"text": "Done"},
        "children": [],
    }


def test_suspends_and_shows_undefined_fallback_python_none() -> None:
    # Upstream: "suspends and shows undefined fallback" — Python analogue uses explicit ``None``.
    root = create_noop_root()
    thenable = Thenable()
    resolved = {"ok": False}

    def AsyncText() -> object:
        if not resolved["ok"]:
            raise Suspend(thenable)
        return create_element("span", {"text": "Done"})

    root.render(suspense(fallback=None, children=create_element(AsyncText)))
    assert root.container.last_committed is None


def test_suspends_and_shows_inner_fallback() -> None:
    # Upstream: nested Suspense — inner fallback wins while inner child suspends.
    root = create_noop_root()
    thenable = Thenable()
    resolved = {"ok": False}

    def AsyncText() -> object:
        if not resolved["ok"]:
            raise Suspend(thenable)
        return create_element("span", {"text": "Done"})

    inner = suspense(
        fallback=create_element("div", {"text": "Loading"}),
        children=create_element(AsyncText),
    )
    root.render(
        suspense(
            fallback=create_element("div", {"text": "outer-fallback"}),
            children=inner,
        )
    )
    assert root.container.last_committed == {
        "type": "div",
        "key": None,
        "props": {"text": "Loading"},
        "children": [],
    }

    resolved["ok"] = True
    thenable.resolve()
    root.flush()
    assert root.container.last_committed == {
        "type": "span",
        "key": None,
        "props": {"text": "Done"},
        "children": [],
    }


def test_suspends_and_shows_inner_null_fallback() -> None:
    root = create_noop_root()
    thenable = Thenable()
    resolved = {"ok": False}

    def AsyncText() -> object:
        if not resolved["ok"]:
            raise Suspend(thenable)
        return create_element("span", {"text": "Done"})

    inner = suspense(fallback=None, children=create_element(AsyncText))
    root.render(
        suspense(
            fallback=create_element("div", {"text": "outer-fallback"}),
            children=inner,
        )
    )
    assert root.container.last_committed is None
    resolved["ok"] = True
    thenable.resolve()
    root.flush()
    assert root.container.last_committed == {
        "type": "span",
        "key": None,
        "props": {"text": "Done"},
        "children": [],
    }


def test_suspends_and_shows_inner_undefined_fallback_python_none() -> None:
    # Upstream inner ``undefined`` fallback — Python uses explicit ``fallback=None``.
    root = create_noop_root()
    thenable = Thenable()
    resolved = {"ok": False}

    def AsyncText() -> object:
        if not resolved["ok"]:
            raise Suspend(thenable)
        return create_element("span", {"text": "Done"})

    inner = suspense(fallback=None, children=create_element(AsyncText))
    root.render(
        suspense(
            fallback=create_element("div", {"text": "outer-fallback"}),
            children=inner,
        )
    )
    assert root.container.last_committed is None
    resolved["ok"] = True
    thenable.resolve()
    root.flush()
    assert root.container.last_committed == {
        "type": "span",
        "key": None,
        "props": {"text": "Done"},
        "children": [],
    }
