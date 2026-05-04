from __future__ import annotations

from typing import Any

from ryact import create_element
from ryact.concurrent import Fragment, suspense_list
from ryact_testkit import create_noop_root
from ryact_testkit.warnings import WarningCapture


def _render_once(element: Any) -> None:
    root = create_noop_root()
    root.render(element)
    root.flush()


def test_warns_if_a_single_element_is_passed_to_a_forwards_list() -> None:
    # Upstream: ReactSuspenseList-test.js — "warns if a single element is passed to a \"forwards\" list"
    with WarningCapture() as cap:
        _render_once(suspense_list(reveal_order="forwards", children=create_element("span")))
    cap.assert_any("SuspenseList")


def test_warns_if_a_single_fragment_is_passed_to_a_backwards_list() -> None:
    # Upstream: ReactSuspenseList-test.js — "warns if a single fragment is passed to a \"backwards\" list"
    with WarningCapture() as cap:
        _render_once(suspense_list(reveal_order="backwards", children=create_element(Fragment, {"children": ()})))
    cap.assert_any("SuspenseList")


def test_warns_if_a_nested_array_is_passed_to_a_forwards_list() -> None:
    # Upstream: ReactSuspenseList-test.js — "warns if a nested array is passed to a \"forwards\" list"
    # Construct a nested array shape that survives the SuspenseList child normalization:
    # `children` becomes a single tuple whose element is a list of elements.
    nested = (([create_element("span")],),)
    with WarningCapture() as cap:
        _render_once(suspense_list(reveal_order="forwards", children=nested))
    cap.assert_any("nested")
