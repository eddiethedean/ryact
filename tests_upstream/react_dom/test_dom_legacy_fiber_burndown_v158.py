# Translated from: packages/react-dom/src/__tests__/ReactDOMLegacyFiber-test.js
# Burndown v158: document fragment mount target.
from __future__ import annotations

from collections.abc import Iterator

import pytest
from ryact import create_element
from ryact.dev import is_dev, set_dev
from ryact_dom.dom import Container
from ryact_dom.dom_internals import reset_component_dom_registry
from ryact_dom.legacy_mount import legacy_render, reset_legacy_mount_state


@pytest.fixture(autouse=True)
def _dev_and_legacy_state() -> Iterator[None]:
    prev = is_dev()
    set_dev(True)
    reset_legacy_mount_state()
    reset_component_dom_registry()
    yield
    reset_legacy_mount_state()
    reset_component_dom_registry()
    set_dev(prev)


def test_should_mount_into_a_document_fragment() -> None:
    fragment = Container.create_document_fragment()
    parent = Container()
    legacy_render(create_element("div", None, "foo"), fragment)
    assert parent.text_content == ""
    parent.adopt_children_from(fragment)
    assert parent.text_content == "foo"
