from __future__ import annotations

from collections.abc import Callable

from ryact import create_element, use_state
from ryact_testkit import create_noop_root


def test_callback_ref_runs_on_mount_update_and_unmount() -> None:
    # Upstream: ReactIncrementalSideEffects-test.js
    # "invokes ref callbacks after insertion/update/unmount"
    log: list[tuple[str, object | None]] = []
    api: dict[str, Callable[[int], None]] = {}

    def ref_cb(value: object | None) -> None:
        log.append(("ref", value))

    def Host() -> object:
        n, set_n = use_state(0)
        api["setN"] = set_n
        return create_element(
            "div",
            {"ref": ref_cb, "data-n": str(n), "text": f"t{n}"},
        )

    root = create_noop_root()
    root.render(create_element(Host))
    assert root.container.last_committed_as_dict()["props"]["data-n"] == "0"
    root.flush()

    api["setN"](1)
    root.flush()
    assert root.container.last_committed_as_dict()["props"]["data-n"] == "1"

    root.render(None)
    root.flush()

    attached = [v for k, v in log if k == "ref" and v is not None]
    assert attached, log
    assert log[-1] == ("ref", None), log
