from __future__ import annotations

from ryact import create_element
from ryact_testkit import create_noop_root


def test_prepareforcommit_and_resetaftercommit_receive_host_context() -> None:
    # Upstream: ReactFiberHostContext-test.internal.js
    # "should send the context to prepareForCommit and resetAfterCommit"
    root = create_noop_root()
    seen: list[tuple[str, object]] = []

    def get_root_host_context() -> object:
        return {"ctx": 1}

    def prepare(ctx: object) -> None:
        seen.append(("prepare", ctx))

    def reset(ctx: object) -> None:
        seen.append(("reset", ctx))

    root.container.get_root_host_context = get_root_host_context  # type: ignore[attr-defined]
    root.container.prepareForCommit = prepare  # type: ignore[attr-defined]
    root.container.resetAfterCommit = reset  # type: ignore[attr-defined]

    root.render(create_element("div", {"text": "x"}))
    assert seen == [("prepare", {"ctx": 1}), ("reset", {"ctx": 1})]

