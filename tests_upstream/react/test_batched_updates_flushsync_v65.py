from __future__ import annotations

from ryact import create_element, use_state
from ryact_testkit import act, create_noop_root, set_act_environment_enabled


def test_flushsync_does_not_flush_batched_work() -> None:
    # Upstream: ReactBatching-test.internal.js
    # "flushSync does not flush batched work"
    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        setters: list[object] = [None]

        def App() -> object:
            v, set_v = use_state(0)
            setters[0] = set_v
            return create_element("span", {"children": [str(v)]})

        with act(flush=root.flush):
            root.render(create_element(App, {}))

        # Batch an update; it should not commit until an explicit flush.
        root.container.commits.clear()

        def do_batched() -> None:
            setters[0](1)  # type: ignore[misc]

        root.batched_updates(do_batched)
        assert root.container.commits == []

        # flushSync should not flush the previously batched update either.
        root.flush_sync(lambda: None)
        assert root.container.commits == []

        # But a normal flush should commit it.
        root.flush()
        assert root.container.commits and "1" in str(root.container.commits[-1])
    finally:
        set_act_environment_enabled(False)
