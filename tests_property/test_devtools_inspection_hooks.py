from __future__ import annotations

from ryact import create_element, inspect_fiber_tree, use_state
from ryact_testkit import create_noop_root


def test_inspect_fiber_tree_includes_props_and_hook_types() -> None:
    root = create_noop_root()

    def App() -> object:
        n, _ = use_state(0)
        return create_element("div", {"value": n})

    root.render(create_element(App))
    tree = inspect_fiber_tree(root._reconciler_root)
    assert tree is not None

    # root -> App -> div
    assert tree.children[0].type == "App"
    assert tree.children[0].hook_types is not None
    assert "_StateHook" in tree.children[0].hook_types
    assert tree.children[0].children[0].type == "div"
    assert tree.children[0].children[0].props is not None
    assert tree.children[0].children[0].props.get("value") == 0
