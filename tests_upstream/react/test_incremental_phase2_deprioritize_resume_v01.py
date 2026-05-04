from __future__ import annotations

from typing import Any

from ryact import create_element
from ryact.reconciler import SYNC_LANE, TRANSITION_LANE
from ryact_testkit import create_noop_root


def _text(value: str) -> Any:
    return create_element("div", {"text": value})


def test_can_deprioritize_unfinished_work_and_resume_it_later() -> None:
    # Upstream: ReactIncremental-test.js
    # "can deprioritize unfinished work and resume it later"
    #
    # Minimal model:
    # - Start a low-priority render that yields before committing.
    # - Schedule a sync update; it should flush first.
    # - Then flush again to allow the earlier deferred update to complete.
    root = create_noop_root(yield_after_nodes=1)

    root.render(_text("deferred"), lane=TRANSITION_LANE)
    root.flush()
    assert root.get_children_snapshot() is None

    root.set_yield_after_nodes(0)
    root.render(_text("sync"), lane=SYNC_LANE)
    root.flush()
    commits = list(root.container.commits)
    assert len(commits) == 2
    assert commits[0]["props"]["text"] == "sync"
    assert commits[1]["props"]["text"] == "deferred"
    assert root.get_children_snapshot()["props"]["text"] == "deferred"
