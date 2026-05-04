from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ryact import create_element, use_state
from ryact.concurrent import start_transition
from ryact_testkit import create_noop_root


def test_sync_lane_commits_before_transition_lane_when_batched() -> None:
    # Upstream family: ReactTransition-test.js
    # Minimal harness contract: when sync + transition updates are queued together,
    # sync lane wins commit order.
    root = create_noop_root()

    api: dict[str, Callable[[], None]] = {}

    def App() -> Any:
        value, set_value = use_state("A")

        def enqueue() -> None:
            start_transition(lambda: set_value("T"))
            set_value("S")

        api["enqueue"] = enqueue
        return create_element("div", {"value": value})

    root.render(create_element(App))

    def do() -> None:
        api["enqueue"]()

    root.batched_updates(do)
    root.flush()
    root.flush()

    commits = root.container.commits
    # Expect to see S committed before T.
    s_commit = {"type": "div", "key": None, "props": {"value": "S"}, "children": []}
    t_commit = {"type": "div", "key": None, "props": {"value": "T"}, "children": []}
    assert s_commit in commits
    assert t_commit in commits
    assert commits.index(s_commit) < commits.index(t_commit)

