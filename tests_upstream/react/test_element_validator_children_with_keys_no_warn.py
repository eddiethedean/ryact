from __future__ import annotations

import warnings

from ryact import create_element
from ryact.dev import is_dev


def test_no_warning_for_array_children_when_each_element_has_key() -> None:
    # Upstream: ReactElementValidator-test.internal.js
    # "does not warns for arrays of elements with keys"
    if not is_dev():
        return
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        create_element(
            "div",
            {
                "children": [
                    create_element("span", {"key": "a", "text": "x"}),
                    create_element("span", {"key": "b", "text": "y"}),
                ],
            },
        )
    key_msgs = [m for m in rec if "key" in str(m.message).lower()]
    assert not key_msgs


def test_no_warning_for_tuple_children_when_each_element_has_key() -> None:
    # Upstream: ReactElementValidator-test.internal.js
    # "does not warns for iterable elements with keys"
    if not is_dev():
        return
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        create_element(
            "div",
            {
                "children": (
                    create_element("span", {"key": "a", "text": "x"}),
                    create_element("span", {"key": "b", "text": "y"}),
                ),
            },
        )
    key_msgs = [m for m in rec if "key" in str(m.message).lower()]
    assert not key_msgs
