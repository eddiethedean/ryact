from __future__ import annotations

from ryact import create_element
from ryact_testkit import create_noop_root


def _text(value: object) -> object:
    return value


def test_renders_string_from_function_component() -> None:
    # Upstream: ReactTopLevelText-test — strings from render
    r = create_noop_root()
    r.render(create_element(_text, {"value": "foo"}))
    r.flush()
    assert r.get_children_snapshot() == "foo"


def test_renders_number_from_function_component() -> None:
    # Upstream: ReactTopLevelText-test — numbers from render
    r = create_noop_root()
    r.render(create_element(_text, {"value": 10}))
    r.flush()
    assert r.get_children_snapshot() == "10"


def test_renders_arbitrary_int_from_function_component() -> None:
    # Upstream: ReactTopLevelText-test — bigints from render (JS BigInt; Python int).
    r = create_noop_root()
    n = 10**18
    r.render(create_element(_text, {"value": n}))
    r.flush()
    assert r.get_children_snapshot() == str(n)
