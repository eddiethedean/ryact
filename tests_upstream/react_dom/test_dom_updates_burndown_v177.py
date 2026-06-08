# Translated from: packages/react-dom/src/__tests__/ReactUpdates-test.js
# Burndown v177: createRoot ref-callback and useEffect flushSync depth guards.
from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from ryact import create_element, use_effect, use_reducer, use_state
from ryact.dev import is_dev, set_dev
from ryact_dom.dom import Container
from ryact_dom.dom_internals import reset_component_dom_registry
from ryact_dom.error_reporting import console_error_log
from ryact_dom.legacy_mount import reset_legacy_mount_state
from ryact_dom.root import create_root
from ryact_dom.root_dev import reset_root_dev_state
from ryact_testkit import act, set_act_environment_enabled


@pytest.fixture(autouse=True)
def _dev_and_reset() -> Iterator[None]:
    prev = is_dev()
    set_dev(True)
    reset_legacy_mount_state()
    reset_root_dev_state()
    reset_component_dom_registry()
    set_act_environment_enabled(True)
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


def test_prevents_infinite_update_loop_triggered_by_synchronous_updates_in_useeffect() -> None:
    c, root = _root()

    def NonTerminating(**props: object) -> object:
        step, set_step = use_state(0)
        dom_root = props["root"]

        def effect() -> None:
            dom_root.flush_sync(lambda: set_step(step + 1))

        use_effect(effect, (step,))
        return create_element("span", None, str(step))

    with act(flush=root.flush_sync):
        root.render(create_element(NonTerminating, {"root": root}))
    assert _has_max_depth_message(c)


def test_prevents_infinite_update_loop_triggered_by_too_many_updates_in_ref_callbacks() -> None:
    c, root = _root()

    def TooManyRefUpdates(**_props: object) -> object:
        count, schedule_update = use_reducer(lambda n: n + 1, 0)

        def ref_cb(_node: object) -> None:
            for _ in range(50):
                schedule_update(1)

        return create_element("div", {"ref": ref_cb}, str(count))

    root.render(create_element(TooManyRefUpdates))
    assert _has_max_depth_message(c)
