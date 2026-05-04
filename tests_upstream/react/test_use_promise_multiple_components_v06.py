from __future__ import annotations

from typing import Any

import pytest
from ryact import create_element
from ryact.concurrent import Thenable, suspense
from ryact.use import use
from ryact_testkit import act, create_noop_root, set_act_environment_enabled


@pytest.mark.asyncio
async def test_use_promise_in_multiple_components() -> None:
    # Upstream: ReactUse-test.js
    # "use(promise) in multiple components"
    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        t = Thenable()

        def A() -> Any:
            v = use(t)
            return create_element("span", {"text": f"A {v}"})

        def B() -> Any:
            v = use(t)
            return create_element("span", {"text": f"B {v}"})

        def App() -> Any:
            return suspense(
                fallback=create_element("span", {"text": "loading"}),
                children=create_element(
                    "div",
                    {
                        "children": [
                            create_element(A, {"key": "a"}),
                            create_element(B, {"key": "b"}),
                        ]
                    },
                ),
            )

        with act(flush=root.flush):
            root.render(create_element(App))
        snap0 = root.get_children_snapshot()
        assert isinstance(snap0, dict)
        assert snap0["props"]["text"] == "loading"

        with act(flush=root.flush):
            t.resolve("ok")
        snap1 = root.get_children_snapshot()
        assert isinstance(snap1, dict)
        assert snap1["type"] == "div"
        children = snap1.get("children") or []
        assert [c["props"]["text"] for c in children if isinstance(c, dict)] == ["A ok", "B ok"]
    finally:
        set_act_environment_enabled(False)


@pytest.mark.asyncio
async def test_use_promise_in_multiple_sibling_components() -> None:
    # Upstream: ReactUse-test.js
    # "use(promise) in multiple sibling components"
    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        t = Thenable()

        def A() -> Any:
            v = use(t)
            return create_element("span", {"text": f"A {v}"})

        def B() -> Any:
            v = use(t)
            return create_element("span", {"text": f"B {v}"})

        def App() -> Any:
            return create_element(
                "div",
                {
                    "children": [
                        create_element(
                            "__suspense__",
                            {
                                "key": "sa",
                                "fallback": create_element("span", {"text": "loading A"}),
                                "children": (create_element(A, {"key": "a"}),),
                            },
                        ),
                        create_element(
                            "__suspense__",
                            {
                                "key": "sb",
                                "fallback": create_element("span", {"text": "loading B"}),
                                "children": (create_element(B, {"key": "b"}),),
                            },
                        ),
                    ]
                },
            )

        with act(flush=root.flush):
            root.render(create_element(App))
        snap0 = root.get_children_snapshot()
        assert isinstance(snap0, dict)
        assert snap0["type"] == "div"
        children0 = snap0.get("children") or []
        assert [c["props"]["text"] for c in children0 if isinstance(c, dict)] == [
            "loading A",
            "loading B",
        ]

        with act(flush=root.flush):
            t.resolve("ok")
        snap1 = root.get_children_snapshot()
        assert isinstance(snap1, dict)
        children1 = snap1.get("children") or []
        assert [c["props"]["text"] for c in children1 if isinstance(c, dict)] == [
            "A ok",
            "B ok",
        ]
    finally:
        set_act_environment_enabled(False)
