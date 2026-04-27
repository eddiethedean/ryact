from __future__ import annotations

from ryact import create_element
from ryact_testkit import create_noop_root


def test_should_send_the_context_to_prepareforcommit_and_resetaftercommit() -> None:
    # Upstream: ReactFiberHostContext-test.internal.js
    root = create_noop_root()
    log: list[tuple[str, object]] = []
    sentinel = object()

    root.container.get_root_host_context = lambda: sentinel  # type: ignore[attr-defined]

    def prepare(ctx: object) -> None:
        log.append(("prepare", ctx))

    def reset(ctx: object) -> None:
        log.append(("reset", ctx))

    root.container.prepareForCommit = prepare  # type: ignore[attr-defined]
    root.container.resetAfterCommit = reset  # type: ignore[attr-defined]

    root.render(create_element("div", {"text": "hi"}))

    assert log == [("prepare", sentinel), ("reset", sentinel)]

