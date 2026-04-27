from __future__ import annotations

from ryact import create_element
from ryact_testkit import create_noop_root


def test_other_ref_still_detaches_when_sibling_ref_detach_throws() -> None:
    # Upstream: ReactIncrementalErrorHandling-test.internal.js
    # "does not interrupt unmounting if detaching a ref throws"
    log: list[str] = []

    def bad_ref(value: object | None) -> None:
        if value is None:
            log.append("bad_detach")
            raise RuntimeError("ref detach boom")
        log.append("bad_attach")

    def good_ref(value: object | None) -> None:
        log.append("good_detach" if value is None else "good_attach")

    root = create_noop_root()
    root.render(
        create_element(
            "div",
            None,
            create_element("span", {"key": "a", "ref": bad_ref, "text": "a"}),
            create_element("span", {"key": "b", "ref": good_ref, "text": "b"}),
        ),
    )
    root.render(None)
    root.flush()
    assert "bad_detach" in log
    assert "good_detach" in log
    assert log.index("bad_detach") < log.index("good_detach")
