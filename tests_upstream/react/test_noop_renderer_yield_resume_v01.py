from __future__ import annotations

from typing import Any

from ryact import create_element
from ryact_testkit import create_noop_root


def _span(t: str) -> Any:
    return create_element("span", {"text": t})


def test_yielding_root_makes_forward_progress_and_commits() -> None:
    """
    Harness guard for Phase A work:

    When yielding is enabled, the first flush may yield (no commit), but subsequent
    flushes should not yield forever at the same point; we must eventually commit.
    """

    def App() -> Any:
        return create_element("div", None, _span("a"), _span("b"), _span("c"), _span("d"))

    root = create_noop_root()
    root.set_yield_after_nodes(1)
    root.render(create_element(App))

    root.flush()
    # Depending on subtree shape and budget, the first flush may yield or may complete.
    if root.get_children_snapshot() is None:
        # Resume: yield should be suppressed after a prior yield so we eventually commit.
        root.flush()
    assert root.get_children_snapshot() is not None

