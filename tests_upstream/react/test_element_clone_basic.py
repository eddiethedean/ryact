from __future__ import annotations

import pytest

from ryact import clone_element, create_element


def test_clone_element_throws_if_passed_none() -> None:
    # Upstream: ReactElementClone-test.js — "throws an error if passed null"
    with pytest.raises(TypeError, match="None"):
        clone_element(None)  # type: ignore[arg-type]


def test_clone_element_overwrites_props() -> None:
    # Upstream: ReactElementClone-test.js — "should overwrite props"
    el = create_element("div", {"id": "a", "title": "t"})
    out = clone_element(el, {"id": "b"})
    assert out.type == "div"
    assert dict(out.props)["id"] == "b"
    assert dict(out.props)["title"] == "t"
