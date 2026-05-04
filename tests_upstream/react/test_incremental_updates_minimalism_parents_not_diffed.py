from __future__ import annotations

from ryact import Component, create_element
from ryact_testkit import create_noop_root


def test_minimalism_should_not_diff_parents_of_setstate_targets() -> None:
    # Upstream: ReactIncrementalUpdatesMinimalism-test.js — "should not diff parents of setState targets"
    #
    # We model this as: updating a leaf should not trigger updateProps on ancestor host nodes.
    leaf: Leaf | None = None

    class Leaf(Component):
        def __init__(self) -> None:
            super().__init__()
            nonlocal leaf
            leaf = self

        def render(self) -> object:
            return create_element("span", {"text": str(self.state.get("n", 0))})

    class App(Component):
        def render(self) -> object:
            return create_element(
                "div",
                {"id": "parent"},
                create_element("div", {"id": "mid"}, create_element(Leaf)),
            )

    root = create_noop_root()
    root.render(create_element(App))
    assert leaf is not None

    root.clear_ops()
    leaf.set_state({"n": 1})
    root.flush()

    # We should see an updateProps for the span (path [0,0,0]) but not for ancestors.
    update_ops = [op for op in root.get_ops() if op.get("op") == "updateProps"]
    paths = [tuple(op["path"]) for op in update_ops]
    assert (0, 0, 0) in paths
    assert (0,) not in paths
    assert (0, 0) not in paths
