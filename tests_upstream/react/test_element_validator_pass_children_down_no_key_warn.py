from __future__ import annotations

import warnings

from ryact import create_element
from ryact.dev import is_dev


def test_no_key_warning_when_passing_keyed_children_through_wrapper() -> None:
    # Upstream: ReactElementValidator-test.internal.js
    # "does not warn for keys when passing children down"
    if not is_dev():
        return

    def Child(props: dict[str, object]) -> object:
        ch = props.get("children", ())
        if not isinstance(ch, tuple):
            ch = (ch,)
        return create_element("div", None, *ch)

    a = create_element("span", {"key": "a", "text": "1"})
    b = create_element("span", {"key": "b", "text": "2"})
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        create_element(Child, {"children": (a, b)})
    key_msgs = [m for m in rec if "key" in str(m.message).lower()]
    assert not key_msgs
