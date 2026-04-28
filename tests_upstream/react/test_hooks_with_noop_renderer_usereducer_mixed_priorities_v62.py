from __future__ import annotations

from ryact import create_element, use_reducer
from ryact.concurrent import start_transition
from ryact_testkit import create_noop_root


def test_usereducer_handles_dispatches_with_mixed_priorities() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "handles dispatches with mixed priorities"
    dispatch_ref: list[object] = [None]

    def reducer(s: int, a: str) -> int:
        return s + 1 if a == "inc" else s

    def App() -> object:
        v, d = use_reducer(reducer, 0)  # type: ignore[misc]
        dispatch_ref[0] = d
        return create_element("span", {"children": [str(v)]})

    root = create_noop_root()
    root.render(create_element(App, {}))
    root.container.commits.clear()

    def queue_updates() -> None:
        # Transition lane (lower priority): should not be visible in the default render.
        start_transition(lambda: dispatch_ref[0]("inc"))  # type: ignore[misc]
        # Default lane update.
        dispatch_ref[0]("inc")  # type: ignore[misc]

    root.batched_updates(queue_updates)
    root.flush()

    # Expect two commits: default lane first (state=1), then transition lane (state=2).
    commits = [str(x) for x in root.container.commits]
    assert any("'children': ['1']" in c for c in commits)
    assert any("'children': ['2']" in c for c in commits)

