from __future__ import annotations

from ryact import create_element, use_effect, use_layout_effect
from ryact_testkit import act, create_noop_root, set_act_environment_enabled


def test_layout_unmounts_on_deletion_are_fired_in_parent_child_order() -> None:
    # Upstream: ReactEffectOrdering-test.js
    # "layout unmounts on deletion are fired in parent -> child order"
    log: list[str] = []

    def Child() -> object:
        def eff() -> object:
            def cleanup() -> None:
                log.append("child")

            return cleanup

        use_layout_effect(eff, ())
        return create_element("span", {"children": ["c"]})

    def Parent(*, show: bool) -> object:
        def eff() -> object:
            def cleanup() -> None:
                log.append("parent")

            return cleanup

        use_layout_effect(eff, ())
        return create_element("div", {"children": [create_element(Child, {})] if show else []})

    set_act_environment_enabled(True)
    root = create_noop_root()
    try:
        with act(flush=root.flush):
            root.render(create_element(Parent, {"show": True}))
        with act(flush=root.flush):
            root.render(None)
    finally:
        set_act_environment_enabled(False)

    assert log == ["parent", "child"]


def test_passive_unmounts_on_deletion_are_fired_in_parent_child_order() -> None:
    # Upstream: ReactEffectOrdering-test.js
    # "passive unmounts on deletion are fired in parent -> child order"
    log: list[str] = []

    def Child() -> object:
        def eff() -> object:
            def cleanup() -> None:
                log.append("child")

            return cleanup

        use_effect(eff, ())
        return create_element("span", {"children": ["c"]})

    def Parent(*, show: bool) -> object:
        def eff() -> object:
            def cleanup() -> None:
                log.append("parent")

            return cleanup

        use_effect(eff, ())
        return create_element("div", {"children": [create_element(Child, {})] if show else []})

    set_act_environment_enabled(True)
    root = create_noop_root()
    try:
        with act(flush=root.flush):
            root.render(create_element(Parent, {"show": True}))
        with act(flush=root.flush):
            root.render(None)
    finally:
        set_act_environment_enabled(False)

    assert log == ["parent", "child"]
