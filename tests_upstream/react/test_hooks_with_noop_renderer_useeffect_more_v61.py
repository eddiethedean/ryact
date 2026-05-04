from __future__ import annotations

from ryact import create_element, memo, use_effect, use_layout_effect
from ryact_testkit import act, create_noop_root, set_act_environment_enabled


def test_useeffect_simple_mount_and_update() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "simple mount and update"
    log: list[str] = []

    def App(*, n: int) -> object:
        def eff() -> object:
            log.append(f"mount:{n}")

            def cleanup() -> None:
                log.append(f"unmount:{n}")

            return cleanup

        use_effect(eff, (n,))
        return create_element("span", {"children": [str(n)]})

    set_act_environment_enabled(True)
    root = create_noop_root()
    try:
        with act(flush=root.flush):
            root.render(create_element(App, {"n": 0}))
        with act(flush=root.flush):
            root.render(create_element(App, {"n": 1}))
    finally:
        set_act_environment_enabled(False)

    assert log == ["mount:0", "unmount:0", "mount:1"]


def test_useeffect_multiple_effects() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "multiple effects"
    log: list[str] = []

    def App(*, n: int) -> object:
        def eff1() -> object:
            log.append(f"mount1:{n}")

            def cleanup() -> None:
                log.append(f"unmount1:{n}")

            return cleanup

        def eff2() -> object:
            log.append(f"mount2:{n}")

            def cleanup() -> None:
                log.append(f"unmount2:{n}")

            return cleanup

        use_effect(eff1, (n,))
        use_effect(eff2, (n,))
        return create_element("span", {"children": [str(n)]})

    set_act_environment_enabled(True)
    root = create_noop_root()
    try:
        with act(flush=root.flush):
            root.render(create_element(App, {"n": 0}))
        with act(flush=root.flush):
            root.render(create_element(App, {"n": 1}))
    finally:
        set_act_environment_enabled(False)

    assert log == [
        "mount1:0",
        "mount2:0",
        "unmount1:0",
        "unmount2:0",
        "mount1:1",
        "mount2:1",
    ]


def test_useeffect_skips_effect_if_inputs_have_not_changed() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "skips effect if inputs have not changed"
    log: list[str] = []

    def App(*, n: int) -> object:
        def eff() -> object:
            log.append(f"mount:{n}")

            def cleanup() -> None:
                log.append(f"unmount:{n}")

            return cleanup

        use_effect(eff, (1,))
        return create_element("span", {"children": [str(n)]})

    set_act_environment_enabled(True)
    root = create_noop_root()
    try:
        with act(flush=root.flush):
            root.render(create_element(App, {"n": 0}))
        with act(flush=root.flush):
            root.render(create_element(App, {"n": 1}))
    finally:
        set_act_environment_enabled(False)

    # deps stable -> no cleanup/mount on update
    assert log == ["mount:0"]


def test_useeffect_unmounts_on_deletion() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "unmounts on deletion"
    log: list[str] = []

    def Child(*, n: int) -> object:
        def eff() -> object:
            log.append(f"mount:{n}")

            def cleanup() -> None:
                log.append(f"unmount:{n}")

            return cleanup

        use_effect(eff, ())
        return create_element("span", {"children": [str(n)]})

    def App(*, show: bool) -> object:
        return create_element(
            "div", {"children": [create_element(Child, {"n": 1})] if show else []}
        )

    set_act_environment_enabled(True)
    root = create_noop_root()
    try:
        with act(flush=root.flush):
            root.render(create_element(App, {"show": True}))
        with act(flush=root.flush):
            root.render(create_element(App, {"show": False}))
    finally:
        set_act_environment_enabled(False)

    assert log == ["mount:1", "unmount:1"]


def test_useeffect_unmounts_on_deletion_after_skipped_effect() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "unmounts on deletion after skipped effect"
    log: list[str] = []

    def Child(*, step: int) -> object:
        def eff() -> object:
            log.append(f"mount:{step}")

            def cleanup() -> None:
                log.append(f"unmount:{step}")

            return cleanup

        # deps are constant, so updates to step will skip effect.
        use_effect(eff, (1,))
        return create_element("span", {"children": [str(step)]})

    def App(*, show: bool, step: int) -> object:
        return create_element(
            "div",
            {"children": [create_element(Child, {"step": step})] if show else []},
        )

    set_act_environment_enabled(True)
    root = create_noop_root()
    try:
        with act(flush=root.flush):
            root.render(create_element(App, {"show": True, "step": 0}))
        with act(flush=root.flush):
            root.render(create_element(App, {"show": True, "step": 1}))
        with act(flush=root.flush):
            root.render(create_element(App, {"show": False, "step": 1}))
    finally:
        set_act_environment_enabled(False)

    assert log == ["mount:0", "unmount:0"]


def test_useeffect_unmounts_all_previous_effects_before_creating_any_new_ones() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "unmounts all previous effects before creating any new ones"
    log: list[str] = []

    def App(*, n: int) -> object:
        def e1() -> object:
            log.append(f"create1:{n}")

            def cleanup() -> None:
                log.append(f"destroy1:{n}")

            return cleanup

        def e2() -> object:
            log.append(f"create2:{n}")

            def cleanup() -> None:
                log.append(f"destroy2:{n}")

            return cleanup

        use_effect(e1, (n,))
        use_effect(e2, (n,))
        return create_element("span", {"children": [str(n)]})

    set_act_environment_enabled(True)
    root = create_noop_root()
    try:
        with act(flush=root.flush):
            root.render(create_element(App, {"n": 0}))
        with act(flush=root.flush):
            root.render(create_element(App, {"n": 1}))
    finally:
        set_act_environment_enabled(False)

    assert log == [
        "create1:0",
        "create2:0",
        "destroy1:0",
        "destroy2:0",
        "create1:1",
        "create2:1",
    ]


def test_useeffect_unmounts_all_previous_effects_between_siblings_before_creating_any_new_ones() -> (
    None
):
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "unmounts all previous effects between siblings before creating any new ones"
    log: list[str] = []

    def Child(*, name: str, n: int) -> object:
        def eff() -> object:
            log.append(f"create:{name}:{n}")

            def cleanup() -> None:
                log.append(f"destroy:{name}:{n}")

            return cleanup

        use_effect(eff, (n,))
        return create_element("span", {"children": [f"{name}{n}"]})

    def App(*, n: int) -> object:
        return create_element(
            "div",
            {
                "children": [
                    create_element(Child, {"name": "A", "n": n}, key="A"),
                    create_element(Child, {"name": "B", "n": n}, key="B"),
                ]
            },
        )

    set_act_environment_enabled(True)
    root = create_noop_root()
    try:
        with act(flush=root.flush):
            root.render(create_element(App, {"n": 0}))
        with act(flush=root.flush):
            root.render(create_element(App, {"n": 1}))
    finally:
        set_act_environment_enabled(False)

    assert log == [
        "create:A:0",
        "create:B:0",
        "destroy:A:0",
        "destroy:B:0",
        "create:A:1",
        "create:B:1",
    ]


def test_useeffect_calls_destroy_for_memoized_components_and_descendants() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # - "calls passive effect destroy functions for memoized components"
    # - "calls passive effect destroy functions for descendants of memoized components"
    log: list[str] = []

    def Grandchild(*, name: str) -> object:
        def eff() -> object:
            log.append(f"mount:{name}")

            def cleanup() -> None:
                log.append(f"unmount:{name}")

            return cleanup

        use_effect(eff, ())
        return create_element("span", {"children": [name]})

    def Inner() -> object:
        def eff() -> object:
            log.append("mount:inner")

            def cleanup() -> None:
                log.append("unmount:inner")

            return cleanup

        use_effect(eff, ())
        return create_element("div", {"children": [create_element(Grandchild, {"name": "gc"})]})

    MemoInner = memo(Inner)

    def App(*, show: bool) -> object:
        return create_element("div", {"children": [create_element(MemoInner, {})] if show else []})

    set_act_environment_enabled(True)
    root = create_noop_root()
    try:
        with act(flush=root.flush):
            root.render(create_element(App, {"show": True}))
        with act(flush=root.flush):
            root.render(create_element(App, {"show": False}))
    finally:
        set_act_environment_enabled(False)

    # Deletion should run descendant cleanups too.
    assert log == ["mount:inner", "mount:gc", "unmount:inner", "unmount:gc"] or log == [
        "mount:inner",
        "mount:gc",
        "unmount:gc",
        "unmount:inner",
    ]


def test_uselayouteffect_fires_after_host_mutation() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "fires layout effects after the host has been mutated"
    seen: list[str] = []

    def App(*, text: str) -> object:
        def lay() -> object:
            # Layout effect should observe already-committed snapshot in noop.
            seen.append(str(root.get_children_snapshot()))
            return None

        use_layout_effect(lay, (text,))
        return create_element("span", {"children": [text]})

    set_act_environment_enabled(True)
    root = create_noop_root()
    try:
        with act(flush=root.flush):
            root.render(create_element(App, {"text": "A"}))
        with act(flush=root.flush):
            root.render(create_element(App, {"text": "B"}))
    finally:
        set_act_environment_enabled(False)

    assert any("'children': ['A']" in s for s in seen)
    assert any("'children': ['B']" in s for s in seen)
