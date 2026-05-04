from __future__ import annotations

from typing import Any

from ryact import create_element
from ryact.concurrent import Suspend, Thenable, fragment, suspense_list
from ryact_testkit import create_noop_root


def _span(value: str) -> Any:
    return create_element("span", {"text": value})


def _suspense(*, fallback: Any, child: Any, key: str) -> Any:
    # Create a keyed Suspense boundary element.
    return create_element("__suspense__", {"fallback": fallback, "children": (child,)}, key=key)


def test_behaves_as_revealorder_forwards_by_default() -> None:
    # Upstream: ReactSuspenseList-test.js
    # "behaves as revealOrder=forwards by default"
    t1, t2 = Thenable(), Thenable()
    s1, s2 = {"ready": False}, {"ready": False}

    def A() -> Any:
        if not s1["ready"]:
            raise Suspend(t1)
        return _span("A")

    def B() -> Any:
        if not s2["ready"]:
            raise Suspend(t2)
        return _span("B")

    root = create_noop_root()
    root.render(
        suspense_list(
            children=fragment(
                _suspense(fallback=_span("A..."), child=create_element(A), key="a"),
                _suspense(fallback=_span("B..."), child=create_element(B), key="b"),
            )
        )
    )
    root.flush()
    # Forwards+hidden tail: after first boundary suspends, hide the tail.
    snap = root.get_children_snapshot()
    assert isinstance(snap, list)
    assert [x["props"]["text"] for x in snap] == ["A..."]


def test_behaves_as_tail_hidden_if_no_tail_option_is_specified() -> None:
    # Upstream: ReactSuspenseList-test.js
    # "behaves as tail=hidden if no tail option is specified"
    t1, t2 = Thenable(), Thenable()
    s1, s2 = {"ready": False}, {"ready": True}

    def A() -> Any:
        if not s1["ready"]:
            raise Suspend(t1)
        return _span("A")

    def B() -> Any:
        if not s2["ready"]:
            raise Suspend(t2)
        return _span("B")

    root = create_noop_root()
    root.render(
        suspense_list(
            children=fragment(
                _suspense(fallback=_span("A..."), child=create_element(A), key="a"),
                _suspense(fallback=_span("B..."), child=create_element(B), key="b"),
            )
        )
    )
    root.flush()
    snap = root.get_children_snapshot()
    assert isinstance(snap, list)
    # Tail defaults to hidden: B is hidden even though it can resolve.
    assert [x["props"]["text"] for x in snap] == ["A..."]
