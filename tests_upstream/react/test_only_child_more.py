from __future__ import annotations

import pytest
from ryact import Children, create_element


def test_should_return_the_only_child() -> None:
    # Upstream: onlyChild-test.js
    # "should return the only child"
    child = create_element("div")
    assert Children.only(child) is child


def test_should_fail_when_passed_two_children() -> None:
    # Upstream: onlyChild-test.js
    # "should fail when passed two children"
    with pytest.raises(ValueError):
        Children.only((create_element("div"), create_element("span")))


def test_should_fail_when_passed_nully_values() -> None:
    # Upstream: onlyChild-test.js
    # "should fail when passed nully values"
    with pytest.raises(ValueError):
        Children.only(None)


def test_should_fail_when_key_value_objects() -> None:
    # Upstream: onlyChild-test.js
    # "should fail when key/value objects"
    with pytest.raises(TypeError):
        Children.only({"a": 1})


def test_should_not_fail_when_passed_interpolated_single_child() -> None:
    # Upstream: onlyChild-test.js
    # "should not fail when passed interpolated single child"
    child = create_element("div")
    # Python analogue: single child in a one-item tuple.
    assert Children.only((child,)) is child
