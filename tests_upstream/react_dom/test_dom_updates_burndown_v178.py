# Translated from: packages/react-dom/src/__tests__/ReactUpdates-test.js
# Burndown v178: cross-component render-phase infinite loop warnings.
from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from ryact import create_element, use_state
from ryact.concurrent import start_transition
from ryact.dev import is_dev, set_dev
from ryact_dom.dom import Container
from ryact_dom.dom_internals import reset_component_dom_registry
from ryact_dom.error_reporting import console_error_log
from ryact_dom.legacy_mount import reset_legacy_mount_state
from ryact_dom.root import create_root
from ryact_dom.root_dev import reset_root_dev_state


@pytest.fixture(autouse=True)
def _dev_and_reset() -> Iterator[None]:
    prev = is_dev()
    set_dev(True)
    reset_legacy_mount_state()
    reset_root_dev_state()
    reset_component_dom_registry()
    yield
    reset_legacy_mount_state()
    reset_root_dev_state()
    reset_component_dom_registry()
    set_dev(prev)


def _root(container: Container | None = None) -> tuple[Container, Any]:
    c = container or Container()
    c.console_error_log = []  # type: ignore[attr-defined]
    c.window_error_log = []  # type: ignore[attr-defined]
    return c, create_root(c)


def _has_max_depth_message(c: Container) -> bool:
    return any("Maximum update depth exceeded" in str(x) for x in console_error_log(c))


def _cross_component_loop_tree(set_state_holder: dict[str, Any]) -> object:
    def App(**props: object) -> object:
        _, set_state = use_state(0)
        set_state_holder["fn"] = set_state
        return create_element("div", None, props.get("children"))

    def Child(**_props: object) -> object:
        set_state_holder["fn"](lambda n: n + 1)
        return None

    return create_element(App, None, create_element(Child, {"step": 0}))


def test_warns_about_potential_infinite_loop_if_theres_a_synchronous_render_phase_update_on_another_component() -> None:
    c, root = _root()
    holder: dict[str, Any] = {}
    root.render(_cross_component_loop_tree(holder))
    assert _has_max_depth_message(c)


def test_warns_about_potential_infinite_loop_if_theres_an_async_render_phase_update_on_another_component() -> None:
    c, root = _root()
    holder: dict[str, Any] = {}
    start_transition(lambda: root.render(_cross_component_loop_tree(holder)))
    assert _has_max_depth_message(c)
