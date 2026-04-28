# Translated: ReactTopLevelFragment + ReactHooksWithNoopRenderer (useMemo) for burndown v51
from __future__ import annotations

from ryact import create_element, use_memo, use_state
from ryact_testkit import act, create_noop_root, set_act_environment_enabled


def test_renders_simple_list_return_at_top_level() -> None:
    def fragment_list() -> object:
        return [
            create_element("div", {"key": "a", "children": ["Hello"]}),
            create_element("div", {"key": "b", "children": ["World"]}),
        ]

    root = create_noop_root()
    root.render(create_element(fragment_list, {}))
    s = str(root.get_children_snapshot())
    assert "Hello" in s and "World" in s


def test_use_memo_recomputes_when_no_deps() -> None:
    calls = 0

    def App() -> object:
        nonlocal calls

        def factory() -> int:
            nonlocal calls
            calls += 1
            return 1

        use_memo(factory, None)  # type: ignore[misc, arg-type]
        s, set_s = use_state(0)
        if s < 1:
            set_s(1)
        return create_element("span", {"children": [str(s)]})

    set_act_environment_enabled(True)
    root = create_noop_root()
    try:
        with act(flush=root.flush):
            root.render(create_element(App, {}))
    finally:
        set_act_environment_enabled(False)
    # Mount + re-render: ``deps is None`` always re-invokes the factory in ryact.
    assert calls == 2


def test_use_memo_skips_factory_when_inputs_unchanged() -> None:
    invocations = 0

    def App() -> object:
        n, _ = use_state(0)  # noqa: F841

        def expensive() -> int:
            nonlocal invocations
            invocations += 1
            return 42

        m = use_memo(expensive, (n,))  # type: ignore[misc]
        return create_element("span", {"children": [str(m)]})

    set_act_environment_enabled(True)
    root = create_noop_root()
    try:
        with act(flush=root.flush):
            root.render(create_element(App, {}))
        with act(flush=root.flush):
            root.render(create_element(App, {}))
    finally:
        set_act_environment_enabled(False)
    assert invocations == 1
