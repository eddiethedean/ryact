from __future__ import annotations

from ryact import create_element
from ryact_testkit import create_noop_root


def test_noop_root_can_yield_and_resume_on_flush() -> None:
    def App() -> None:
        return create_element("div", {"children": ["hi"]})

    root = create_noop_root(yield_after_nodes=1)
    root.render(create_element(App))

    # Work should have been paused before committing anything.
    assert root.container.commits == []

    # Disable yielding and resume.
    rr = root._reconciler_root
    rr._yield_after_nodes = 0  # type: ignore[attr-defined]
    root.flush()
    assert root.container.commits == [{"type": "div", "key": None, "props": {}, "children": ["hi"]}]

