from __future__ import annotations

import warnings

from ryact import create_element
from ryact.dev import is_dev


def test_create_element_with_none_type_and_two_children_does_not_blow_up() -> None:
    # Upstream: ReactElementValidator-test.internal.js
    # "does not blow up on key warning with undefined type"
    if not is_dev():
        return
    with warnings.catch_warnings():
        warnings.simplefilter("always")
        create_element(
            None,
            {
                "children": (
                    create_element("span", {"text": "a"}),
                    create_element("span", {"text": "b"}),
                ),
            },
        )
