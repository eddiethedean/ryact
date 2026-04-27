from __future__ import annotations

import warnings

from ryact import create_element
from ryact.dev import is_dev


def test_does_not_warn_when_host_children_include_non_elements_between_single_element() -> None:
    # Upstream: ReactElementValidator-test.internal.js
    # "does not warn when the array contains a non-element"
    if not is_dev():
        return
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        create_element(
            "div",
            None,
            create_element("span", {"text": "only"}),
            "text",
        )
    key_msgs = [m for m in rec if "key" in str(m.message).lower()]
    assert not key_msgs
