from __future__ import annotations

import pytest

from ryact import Component, create_element
from ryact_testkit import WarningCapture, act, create_noop_root, set_act_environment_enabled


@pytest.fixture(autouse=True)
def _reset_act_environment_enabled() -> object:
    # Prevent global leakage across the suite.
    set_act_environment_enabled(False)
    try:
        yield None
    finally:
        set_act_environment_enabled(False)


def test_warns_about_unwrapped_updates_only_if_environment_flag_is_enabled() -> None:
    # Upstream: ReactActWarnings-test.js
    class App(Component):
        def render(self) -> object:
            return create_element("div")

    root = create_noop_root()

    set_act_environment_enabled(False)
    with WarningCapture() as wc:
        root.render(create_element(App))
    assert wc.messages == []

    set_act_environment_enabled(True)
    with WarningCapture() as wc2:
        root.render(create_element(App))
    wc2.assert_any("not wrapped in act")


def test_warns_even_if_update_is_synchronous() -> None:
    # Upstream: ReactActWarnings-test.js
    class App(Component):
        def render(self) -> object:
            return create_element("div")

    root = create_noop_root()
    set_act_environment_enabled(True)
    with WarningCapture() as wc:
        root.render(create_element(App))
    wc.assert_any("not wrapped in act")


def test_warns_if_class_update_is_not_wrapped() -> None:
    # Upstream: ReactActWarnings-test.js
    class App(Component):
        def componentDidMount(self) -> None:
            self.set_state({"n": 1})

        def render(self) -> object:
            return create_element("div", {"text": str(self.state.get("n", 0))})

    root = create_noop_root()
    set_act_environment_enabled(True)
    with WarningCapture() as wc:
        root.render(create_element(App))
    wc.assert_any("class component")


def test_warns_if_root_update_is_not_wrapped() -> None:
    # Upstream: ReactActWarnings-test.js
    class App(Component):
        def render(self) -> object:
            return create_element("div")

    root = create_noop_root()
    set_act_environment_enabled(True)
    with WarningCapture() as wc:
        root.render(create_element(App))
    wc.assert_any("root")


def test_does_not_warn_when_wrapped_in_act() -> None:
    # Sanity: our act() wrapper should suppress unwrapped warnings.
    class App(Component):
        def componentDidMount(self) -> None:
            self.set_state({"n": 1})

        def render(self) -> object:
            return create_element("div", {"text": str(self.state.get("n", 0))})

    root = create_noop_root()
    set_act_environment_enabled(True)
    with WarningCapture() as wc:
        with act(root.flush):
            root.render(create_element(App))
    assert wc.messages == []

