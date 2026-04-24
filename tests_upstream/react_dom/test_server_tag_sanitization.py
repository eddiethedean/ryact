from __future__ import annotations

import pytest
from ryact import create_element
from ryact_dom import render_to_string


def test_throws_for_attack_vector_tag_server_side() -> None:
    # Upstream: ReactDOMComponent-test.js
    # "should throw when an attack vector is used server-side"
    with pytest.raises(ValueError):
        render_to_string(create_element("script><img"))


def test_throws_for_invalid_tag_name_server_side() -> None:
    # Upstream: ReactDOMComponent-test.js
    # "should throw when an invalid tag name is used server-side"
    with pytest.raises(ValueError):
        render_to_string(create_element("div>"))
