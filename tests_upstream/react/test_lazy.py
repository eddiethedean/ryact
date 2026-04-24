from __future__ import annotations

from ryact import create_element
from ryact.concurrent import lazy
from ryact_testkit import create_noop_root


def test_can_resolve_synchronously_without_suspending() -> None:
    # Upstream: ReactLazy-test.internal.js
    # "can resolve synchronously without suspending"
    root = create_noop_root()

    loads = {"count": 0}

    def Inner() -> object:
        return create_element("span", {"text": "Hi"})

    def loader() -> object:
        loads["count"] += 1
        return Inner

    LazyInner = lazy(loader)

    root.render(create_element(LazyInner))
    assert loads["count"] == 1
    assert root.container.last_committed == {
        "type": "span",
        "key": None,
        "props": {"text": "Hi"},
        "children": [],
    }

    root.render(create_element(LazyInner))
    assert loads["count"] == 1
