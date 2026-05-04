from __future__ import annotations

from typing import Any

from ryact import Component, create_element
from ryact_testkit import WarningCapture, create_noop_root, set_act_environment_enabled


def test_warns_about_unwrapped_updates_only_if_environment_flag_is_enabled() -> None:
    # Upstream: ReactActWarnings-test.js
    # "warns about unwrapped updates only if environment flag is enabled"
    root = create_noop_root()

    set_act_environment_enabled(False)
    with WarningCapture() as cap1:
        root.render(create_element("div", {"children": ["x"]}))
    assert not any("not wrapped in act" in m.lower() for m in cap1.messages)

    set_act_environment_enabled(True)
    with WarningCapture() as cap2:
        root.render(create_element("div", {"children": ["y"]}))
    assert any("not wrapped in act" in m.lower() for m in cap2.messages)


def test_warns_even_if_update_is_synchronous() -> None:
    # Upstream: ReactActWarnings-test.js
    # "warns even if update is synchronous"
    root = create_noop_root()
    set_act_environment_enabled(True)
    with WarningCapture() as cap:
        # No scheduler => work flushes synchronously for noop roots.
        root.render(create_element("div", {"children": ["sync"]}))
    assert any("not wrapped in act" in m.lower() for m in cap.messages)


def test_warns_if_root_update_is_not_wrapped() -> None:
    # Upstream: ReactActWarnings-test.js
    # "warns if root update is not wrapped"
    root = create_noop_root()
    set_act_environment_enabled(True)
    with WarningCapture() as cap:
        root.render(create_element("div", {"children": ["root-update"]}))
    assert any("update to the root" in m.lower() and "act" in m.lower() for m in cap.messages)


def test_warns_if_class_update_is_not_wrapped() -> None:
    # Upstream: ReactActWarnings-test.js
    # "warns if class update is not wrapped"
    inst: list[Any] = []

    class Counter(Component[dict[str, Any]]):
        def __init__(self, **props: Any) -> None:
            super().__init__(**props)
            inst.append(self)

        def render(self) -> object:
            return create_element("div", {"children": ["ok"]})

    root = create_noop_root()
    set_act_environment_enabled(True)
    root.render(create_element(Counter, {}))
    c = inst[0]

    with WarningCapture() as cap:
        c.set_state({"n": 1})
    assert any("class component" in m.lower() and "act" in m.lower() for m in cap.messages)
