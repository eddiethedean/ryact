from __future__ import annotations

import warnings

from ryact import create_element
from ryact.dev import is_dev


def test_no_missing_key_warning_when_single_element_in_rest_args() -> None:
    # Upstream: ReactElementValidator-test.internal.js
    # "does not warn when the element is directly in rest args"
    if not is_dev():
        return
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        create_element("div", None, create_element("span", {"text": "only"}))
    key_msgs = [m for m in rec if "key" in str(m.message).lower()]
    assert not key_msgs
