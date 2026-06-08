# Translated from: packages/react-dom/src/__tests__/ReactLegacyMount-test.js
# Burndown v180: legacy render at a comment mount point.
from __future__ import annotations

from collections.abc import Iterator

import pytest
from ryact import Fragment, create_element
from ryact.dev import is_dev, set_dev
from ryact_dom.dom import make_comment_mount_shell
from ryact_dom.dom_internals import reset_component_dom_registry
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


def _char_list(chars: str) -> object:
    def Char(**props: object) -> object:
        return create_element("span", None, props.get("children"))

    return create_element(
        Fragment,
        None,
        *[create_element(Char, {"key": ch, "children": ch}) for ch in chars],
    )


def test_renders_at_a_comment_node() -> None:
    shell, mount = make_comment_mount_shell(before="A", after=" B")
    legacy_render(_char_list("aeiou"), mount)
    assert shell.text_content == "Aaeiou B"
    legacy_render(_char_list("yea"), mount)
    assert shell.text_content == "Ayea B"
    legacy_render(None, mount)
    assert shell.text_content == "A B"
