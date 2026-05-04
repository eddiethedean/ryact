from __future__ import annotations

import pytest
from ryact import Component, create_element
from ryact_testkit import create_noop_root


def test_does_not_update_child_nodes_if_a_flush_is_aborted() -> None:
    # Upstream: ReactIncrementalSideEffects-test.js
    # "does not update child nodes if a flush is aborted"
    root = create_noop_root()

    root.render(create_element("div", {"text": "A"}))
    before = root.container.last_committed
    assert before == {"type": "div", "key": None, "props": {"text": "A"}, "children": []}

    class Boom(Component):
        def render(self) -> object:
            raise RuntimeError("boom")

    # Aborted flush (render throws). Noop root retries once; ensure it still fails.
    with pytest.raises(RuntimeError, match="boom"):
        root.render(create_element("div", {"text": "B"}, create_element(Boom)))

    # Since the flush never commits, the previously committed host tree is preserved.
    assert root.container.last_committed == before
