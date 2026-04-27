from __future__ import annotations

from ryact import Fragment, create_element
from ryact.dev import set_dev
from ryact_testkit import WarningCapture


def test_warns_for_fragments_with_illegal_attributes() -> None:
    # Upstream: ReactElementValidator-test.internal.js
    # "warns for fragments with illegal attributes"
    set_dev(True)
    with WarningCapture() as cap:
        create_element(Fragment, {"className": "illegal"}, "child")
    assert any("fragment" in str(m).lower() for m in cap.messages)
    assert any("className" in str(m) for m in cap.messages)
