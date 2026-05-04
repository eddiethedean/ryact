from __future__ import annotations

from typing import Any

import pytest

from ryact import Component, create_element
from ryact.concurrent import Thenable
from ryact_testkit import act, create_noop_root, set_act_environment_enabled


@pytest.mark.asyncio
async def test_async_children_are_transparently_unwrapped_top_level() -> None:
    # Upstream: ReactUse-test.js
    # "async children are transparently unwrapped before being reconciled (top level)"
    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        t = Thenable()
        t.resolve(create_element("span", {"text": "hi"}))

        with act(flush=root.flush):
            root.render(t)
        snap = root.get_children_snapshot()
        assert isinstance(snap, dict)
        assert snap["type"] == "span"
        assert snap["props"]["text"] == "hi"
    finally:
        set_act_environment_enabled(False)


@pytest.mark.asyncio
async def test_async_children_are_transparently_unwrapped_siblings() -> None:
    # Upstream: ReactUse-test.js
    # "async children are transparently unwrapped before being reconciled (siblings)"
    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        t1 = Thenable()
        t2 = Thenable()
        t1.resolve(create_element("span", {"text": "A"}))
        t2.resolve(create_element("span", {"text": "B"}))

        with act(flush=root.flush):
            root.render(create_element("div", {"children": [t1, t2]}))
        snap = root.get_children_snapshot()
        assert isinstance(snap, dict)
        assert snap["type"] == "div"
        children = snap.get("children") or []
        assert [c["props"]["text"] for c in children if isinstance(c, dict)] == ["A", "B"]
    finally:
        set_act_environment_enabled(False)


@pytest.mark.asyncio
async def test_async_children_are_transparently_unwrapped_siblings_reordered() -> None:
    # Upstream: ReactUse-test.js
    # "async children are transparently unwrapped before being reconciled (siblings, reordered)"
    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        t1 = Thenable()
        t2 = Thenable()
        t1.resolve(create_element("span", {"text": "A"}))
        t2.resolve(create_element("span", {"text": "B"}))

        with act(flush=root.flush):
            root.render(create_element("div", {"children": [t1, t2]}))
        with act(flush=root.flush):
            root.render(create_element("div", {"children": [t2, t1]}))
        snap = root.get_children_snapshot()
        assert isinstance(snap, dict)
        children = snap.get("children") or []
        assert [c["props"]["text"] for c in children if isinstance(c, dict)] == ["B", "A"]
    finally:
        set_act_environment_enabled(False)


@pytest.mark.asyncio
async def test_async_children_are_recursively_unwrapped() -> None:
    # Upstream: ReactUse-test.js
    # "async children are recursively unwrapped"
    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        inner = Thenable()
        outer = Thenable()
        inner.resolve(create_element("span", {"text": "hi"}))
        outer.resolve(inner)

        with act(flush=root.flush):
            root.render(outer)
        snap = root.get_children_snapshot()
        assert isinstance(snap, dict)
        assert snap["type"] == "span"
        assert snap["props"]["text"] == "hi"
    finally:
        set_act_environment_enabled(False)


@pytest.mark.asyncio
async def test_async_child_of_a_non_function_component_class() -> None:
    # Upstream: ReactUse-test.js
    # "async child of a non-function component (e.g. a class)"
    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        t = Thenable()
        t.resolve(create_element("span", {"text": "hi"}))

        class App(Component):
            def render(self) -> Any:
                return t

        with act(flush=root.flush):
            root.render(create_element(App))
        snap = root.get_children_snapshot()
        assert isinstance(snap, dict)
        assert snap["type"] == "span"
        assert snap["props"]["text"] == "hi"
    finally:
        set_act_environment_enabled(False)

