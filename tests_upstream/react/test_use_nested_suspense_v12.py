from __future__ import annotations

from typing import Any

from ryact import create_element, use
from ryact.concurrent import Thenable
from ryact_testkit import create_noop_root


def _span(text: str, *, key: str | None = None) -> Any:
    props: dict[str, Any] = {"text": text}
    if key is not None:
        props["key"] = key
    return create_element("span", props)


def _nested_app(t1: Thenable, t2: Thenable) -> Any:
    def Inner() -> Any:
        v2 = use(t2)
        return _span(f"i:{v2}", key="i")

    def Outer() -> Any:
        v1 = use(t1)
        inner_boundary = create_element(
            "__suspense__",
            {
                "key": "in-sus",
                "fallback": _span("inner-fb", key="ifb"),
                "children": (create_element(Inner, {"key": "inner"}),),
            },
        )
        return create_element(
            "div",
            {
                "children": [
                    _span(f"o:{v1}", key="o"),
                    inner_boundary,
                ]
            },
        )

    def App() -> Any:
        return create_element(
            "__suspense__",
            {
                "key": "out-sus",
                "fallback": _span("outer-fb", key="ofb"),
                "children": (create_element(Outer, {"key": "outer"}),),
            },
        )

    return App


def test_load_multiple_nested_suspense_boundaries() -> None:
    # Upstream: ReactUse-test.js — "load multiple nested Suspense boundaries"
    t1 = Thenable()
    t2 = Thenable()
    root = create_noop_root()
    root.render(create_element(_nested_app(t1, t2)))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "outer-fb"

    t1.resolve("a")
    root.flush()
    snap = root.get_children_snapshot()
    assert snap["type"] == "div"
    ch = snap.get("children") or []
    texts = [c["props"]["text"] for c in ch if isinstance(c, dict)]
    assert texts == ["o:a", "inner-fb"]

    t2.resolve("b")
    root.flush()
    snap2 = root.get_children_snapshot()
    assert snap2["type"] == "div"
    ch2 = snap2.get("children") or []
    texts2 = [c["props"]["text"] for c in ch2 if isinstance(c, dict)]
    assert texts2 == ["o:a", "i:b"]


def test_load_multiple_nested_suspense_boundaries_uncached_requests() -> None:
    # Upstream: ReactUse-test.js — "load multiple nested Suspense boundaries (uncached requests)"
    #
    # We do not model React's `cache()`; Thenables here are ordinary per-test promises (uncached
    # in the React 19 resource sense). Waterfall matches nested Suspense resolution order.
    t1 = Thenable()
    t2 = Thenable()
    root = create_noop_root()
    root.render(create_element(_nested_app(t1, t2)))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "outer-fb"
    t1.resolve("1")
    root.flush()
    snap = root.get_children_snapshot()
    assert snap["type"] == "div"
    ch = snap.get("children") or []
    assert [c["props"]["text"] for c in ch if isinstance(c, dict)] == ["o:1", "inner-fb"]
    t2.resolve("2")
    root.flush()
    snap2 = root.get_children_snapshot()
    ch2 = snap2.get("children") or []
    assert [c["props"]["text"] for c in ch2 if isinstance(c, dict)] == ["o:1", "i:2"]
