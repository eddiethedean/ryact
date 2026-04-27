from __future__ import annotations

import pytest

from ryact import create_element, forward_ref
from ryact_testkit import WarningCapture, create_noop_root


def test_strings_refs_can_be_codemodded_to_callback_refs() -> None:
    # Upstream: ReactFiberRefs-test.js — "strings refs can be codemodded to callback refs"
    root = create_noop_root()
    with WarningCapture() as cap:
        root.render(create_element("div", {"ref": "legacy"}))
    assert any("string refs" in str(r.message).lower() for r in cap.records)


def test_throw_if_a_string_ref_is_passed_to_a_ref_receiving_component() -> None:
    # Upstream: ReactFiberRefs-test.js — "throw if a string ref is passed to a ref-receiving component"
    Fancy = forward_ref(lambda _props, _ref: create_element("div"))
    root = create_noop_root()
    with pytest.raises(TypeError, match="String refs are not supported"):
        root.render(create_element(Fancy, {"ref": "legacy"}))

