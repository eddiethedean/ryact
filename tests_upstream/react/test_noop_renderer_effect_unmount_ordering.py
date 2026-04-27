from __future__ import annotations

from collections.abc import Callable

from ryact import create_element
from ryact.hooks import use_effect
from ryact_testkit import create_noop_root


def test_deleted_subtree_effect_cleanups_run() -> None:
    log: list[str] = []

    def Child(*, name: str) -> None:

        def eff() -> Callable[[], None]:
            log.append(f"mount:{name}")

            def cleanup() -> None:
                log.append(f"cleanup:{name}")

            return cleanup

        use_effect(eff, [])
        return None

    def App(*, show_a: bool) -> None:
        if show_a:
            return create_element(Child, {"name": "A"}, key="A")
        return create_element(Child, {"name": "B"}, key="B")

    root = create_noop_root()
    root.render(create_element(App, {"show_a": True}))
    assert log == ["mount:A"]

    root.render(create_element(App, {"show_a": False}))
    # A must clean up before B mounts in the next commit.
    assert log == ["mount:A", "cleanup:A", "mount:B"]

