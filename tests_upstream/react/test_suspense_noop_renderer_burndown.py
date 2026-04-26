from __future__ import annotations

from ryact import create_element
from ryact.concurrent import Suspend, Thenable, fragment, suspense
from ryact_testkit import create_noop_root


def test_suspense_handles_more_than_one_suspended_child_sequentially() -> None:
    # Upstream: ReactSuspenseWithNoopRenderer-test.js
    # "a Suspense component correctly handles more than one suspended child"
    t1, t2 = Thenable(), Thenable()
    r1, r2 = {"ok": False}, {"ok": False}

    def A() -> object:
        if not r1["ok"]:
            raise Suspend(t1)
        return create_element("span", {"text": "A"})

    def B() -> object:
        if not r2["ok"]:
            raise Suspend(t2)
        return create_element("span", {"text": "B"})

    root = create_noop_root()
    root.render(
        suspense(
            fallback=create_element("div", {"text": "Loading"}),
            children=fragment(create_element(A), create_element(B)),
        )
    )
    assert root.container.last_committed == {
        "type": "div",
        "key": None,
        "props": {"text": "Loading"},
        "children": [],
    }

    r1["ok"] = True
    t1.resolve()
    root.flush()
    assert root.container.last_committed == {
        "type": "div",
        "key": None,
        "props": {"text": "Loading"},
        "children": [],
    }

    r2["ok"] = True
    t2.resolve()
    root.flush()
    committed = root.container.last_committed
    assert isinstance(committed, list)
    assert len(committed) == 2
    assert committed[0]["props"]["text"] == "A"
    assert committed[1]["props"]["text"] == "B"
