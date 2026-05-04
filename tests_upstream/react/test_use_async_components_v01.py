from __future__ import annotations

from typing import Any, AsyncGenerator

from ryact import create_element
from ryact_testkit import WarningCapture, create_noop_root


def test_basic_async_component() -> None:
    # Upstream: ReactUse-test.js
    # "basic async component"
    async def App() -> Any:  # type: ignore[func-returns-value]
        return create_element("span", {"text": "hi"})

    root = create_noop_root()
    with WarningCapture() as wc:
        root.render(create_element(App))
        root.flush()
    wc.assert_any("Async generator components are not supported")
    assert root.get_children_snapshot() is None


def test_async_generator_component() -> None:
    # Upstream: ReactUse-test.js
    # "async generator component"
    async def App() -> AsyncGenerator[Any, None]:  # type: ignore[func-returns-value]
        yield create_element("span", {"text": "hi"})

    root = create_noop_root()
    with WarningCapture() as wc:
        root.render(create_element(App))
        root.flush()
    wc.assert_any("Async generator components are not supported")
    assert root.get_children_snapshot() is None

