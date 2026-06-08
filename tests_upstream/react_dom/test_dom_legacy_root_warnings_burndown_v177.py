# Translated from: packages/react-dom/src/__tests__/ReactLegacyRootWarnings-test.js
# Burndown v177: ReactDOM.render deprecation warning.
from __future__ import annotations

from collections.abc import Iterator

import pytest
from ryact import create_element
from ryact.dev import is_dev, set_dev
from ryact_dom.dom import Container
from ryact_dom.dom_internals import reset_component_dom_registry
from ryact_dom.error_reporting import LEGACY_RENDER_DEPRECATION, console_error_log
from ryact_dom.legacy_mount import legacy_render, reset_legacy_mount_state


@pytest.fixture(autouse=True)
def _dev_and_legacy() -> Iterator[None]:
    prev = is_dev()
    set_dev(True)
    reset_legacy_mount_state()
    reset_component_dom_registry()
    yield
    reset_legacy_mount_state()
    reset_component_dom_registry()
    set_dev(prev)


def test_deprecation_warning_for_reactdom_render() -> None:
    c = Container()
    c.console_error_log = []  # type: ignore[attr-defined]
    legacy_render(create_element("span", None, "Hi"), c)
    assert any(LEGACY_RENDER_DEPRECATION in str(x) for x in console_error_log(c))
