from __future__ import annotations

from ryact import create_element


def test_self_and_source_are_treated_as_normal_props() -> None:
    # Upstream: ReactElementValidator-test.internal.js
    # "__self and __source are treated as normal props"
    el = create_element(
        "div",
        {"__self": {"k": 1}, "__source": {"fileName": "x.py"}, "id": "root"},
    )
    props = dict(el.props)
    assert props["__self"] == {"k": 1}
    assert props["__source"] == {"fileName": "x.py"}
    assert props["id"] == "root"
