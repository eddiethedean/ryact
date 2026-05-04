from __future__ import annotations

from ryact import create_element
from ryact.concurrent import Suspend, Thenable, suspense
from ryact.reconciler import TRANSITION_LANE
from ryact_testkit import create_noop_root


def test_flushsync_does_not_flush_batched_work() -> None:
    # Upstream: ReactBatching-test.internal.js — "flushSync does not flush batched work"
    root = create_noop_root()
    root.render(create_element("div", {"text": "init"}))
    assert root.get_children_snapshot()["props"]["text"] == "init"

    def batch() -> None:
        root.render(create_element("div", {"text": "A"}), lane=TRANSITION_LANE)
        root.render(create_element("div", {"text": "B"}), lane=TRANSITION_LANE)

    root.batched_updates(batch)
    # Should not flush until explicitly flushed.
    assert root.get_children_snapshot()["props"]["text"] == "init"

    root.flush_sync(lambda: None)
    # flushSync shouldn't implicitly flush pending batched work.
    assert root.get_children_snapshot()["props"]["text"] == "init"

    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "B"


def test_updates_flush_without_yielding_in_next_event() -> None:
    # Upstream: ReactBatching-test.internal.js — "updates flush without yielding in the next event"
    root = create_noop_root()
    root.render(create_element("div", {"text": "init"}))
    root.batched_updates(lambda: root.render(create_element("div", {"text": "A"})))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "A"


def test_uses_proper_suspense_semantics_not_legacy_ones() -> None:
    # Upstream: ReactBatching-test.internal.js — "uses proper Suspense semantics, not legacy ones"
    thenable = Thenable()

    def Suspender(**_: object) -> object:
        raise Suspend(thenable)

    root = create_noop_root()
    root.render(
        suspense(
            fallback=create_element("div", {"text": "loading"}),
            children=create_element(Suspender),
        )
    )
    assert root.get_children_snapshot()["props"]["text"] == "loading"
    thenable.resolve()
    root.flush()
