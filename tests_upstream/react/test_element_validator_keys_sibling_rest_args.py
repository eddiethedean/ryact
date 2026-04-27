from __future__ import annotations

from ryact import create_element
from ryact.dev import set_dev
from ryact_testkit import WarningCapture


def test_warns_for_missing_keys_when_multiple_sibling_elements_in_rest_args() -> None:
    # Upstream: ReactElementValidator-test.internal.js
    # "warns for keys for arrays of elements in rest args"
    set_dev(True)
    with WarningCapture() as cap:
        create_element(
            "div",
            None,
            create_element("span", None, "a"),
            create_element("span", None, "b"),
        )
    assert any("key" in m.lower() for m in cap.messages)
