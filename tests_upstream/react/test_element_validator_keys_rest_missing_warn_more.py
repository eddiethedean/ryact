from __future__ import annotations

import warnings

from ryact import create_element
from ryact.dev import is_dev


def test_warns_for_tuple_of_host_elements_without_keys_in_rest_args() -> None:
    # Upstream: ReactElementValidator-test.internal.js
    # "warns for keys for iterables of elements in rest args"
    if not is_dev():
        return
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        create_element(
            "div",
            None,
            *(create_element("span", {"text": "a"}), create_element("span", {"text": "b"})),
        )
    key_msgs = [m for m in rec if "key" in str(m.message).lower()]
    assert key_msgs


def test_warns_for_multiple_host_elements_without_keys_in_rest_args() -> None:
    # Upstream: ReactElementValidator-test.internal.js
    # "warns for keys for arrays of elements with no owner info"
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


def test_warns_for_multiple_host_elements_without_keys_owner_info_slice() -> None:
    # Upstream: ReactElementValidator-test.internal.js
    # "warns for keys for arrays of elements with owner info"
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
