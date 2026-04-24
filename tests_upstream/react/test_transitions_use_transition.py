from __future__ import annotations

from collections.abc import Callable

from ryact import create_element, use_state, use_transition
from ryact_testkit import create_noop_root


def test_is_pending_toggles_during_transition() -> None:
    # Upstream: ReactTransition-test.js / ReactAsyncActions-test.js family
    # Minimal contract: useTransition exposes a pending flag during a transition update.
    root = create_noop_root()

    api: dict[str, Callable[[], None]] = {}

    def App() -> object:
        value, set_value = use_state("A")
        pending, start = use_transition()

        def do_transition() -> None:
            start(lambda: set_value("T"))

        api["do"] = do_transition
        return create_element("div", {"value": value, "pending": pending})

    root.render(create_element(App))
    api["do"]()
    root.flush()
    root.flush()

    expected_true = {
        "type": "div",
        "key": None,
        "props": {"value": "T", "pending": True},
        "children": [],
    }
    expected_false = {
        "type": "div",
        "key": None,
        "props": {"value": "T", "pending": False},
        "children": [],
    }
    commits = root.container.commits
    i = commits.index(expected_true)
    assert expected_false in commits[i + 1 :]
