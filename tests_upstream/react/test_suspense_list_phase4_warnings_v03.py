from __future__ import annotations

from typing import Any

from ryact import create_element
from ryact.concurrent import suspense_list
from ryact_testkit import create_noop_root
from ryact_testkit.warnings import WarningCapture


def _render_once(element: Any) -> None:
    root = create_noop_root()
    root.render(element)
    root.flush()


def test_warns_if_a_misspelled_revealorder_option_is_used() -> None:
    # Upstream: ReactSuspenseList-test.js — "warns if a misspelled revealOrder option is used"
    with WarningCapture() as cap:
        _render_once(suspense_list(reveal_order="forwadrs", children=create_element("span")))
    cap.assert_any("revealOrder")


def test_warns_if_a_upper_case_revealorder_option_is_used() -> None:
    # Upstream: ReactSuspenseList-test.js — "warns if a upper case revealOrder option is used"
    with WarningCapture() as cap:
        _render_once(suspense_list(reveal_order="Forwards", children=create_element("span")))
    cap.assert_any("revealOrder")


def test_warns_if_an_unsupported_revealorder_option_is_used() -> None:
    # Upstream: ReactSuspenseList-test.js — "warns if an unsupported revealOrder option is used"
    with WarningCapture() as cap:
        _render_once(suspense_list(reveal_order="random", children=create_element("span")))
    cap.assert_any("revealOrder")


def test_warns_if_an_unsupported_tail_option_is_used() -> None:
    # Upstream: ReactSuspenseList-test.js — "warns if an unsupported tail option is used"
    with WarningCapture() as cap:
        _render_once(
            suspense_list(reveal_order="forwards", tail="random", children=create_element("span"))
        )
    cap.assert_any("tail")


def test_warns_if_a_tail_option_is_used_with_together() -> None:
    # Upstream: ReactSuspenseList-test.js — "warns if a tail option is used with \"together\""
    with WarningCapture() as cap:
        _render_once(
            suspense_list(reveal_order="together", tail="hidden", children=create_element("span"))
        )
    cap.assert_any("tail")
