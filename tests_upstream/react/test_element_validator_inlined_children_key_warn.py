from __future__ import annotations

import warnings

from ryact import create_element
from ryact.dev import is_dev


def test_does_not_blow_up_with_inlined_children_when_missing_keys() -> None:
    # Upstream: ReactElementValidator-test.internal.js
    # "does not blow up with inlined children"
    if not is_dev():
        return
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        create_element(
            "div",
            None,
            create_element("span", {"text": "a"}),
            create_element("span", {"text": "b"}),
        )
    key_msgs = [m for m in rec if "key" in str(m.message).lower()]
    assert key_msgs
