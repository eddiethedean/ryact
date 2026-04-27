from __future__ import annotations

from ryact import Component, create_element
from ryact_testkit import create_noop_root


def test_does_not_call_callbacks_scheduled_by_another_callback_until_later_commit() -> None:
    # Upstream: ReactIncrementalUpdates-test.js —
    # "does not call callbacks that are scheduled by another callback until a later commit"
    log: list[str] = []

    class App(Component):
        def componentDidMount(self) -> None:
            def cb1() -> None:
                log.append("cb1")

                def cb2() -> None:
                    log.append("cb2")

                self.set_state({"n": 2}, callback=cb2)

            self.set_state({"n": 1}, callback=cb1)

        def render(self) -> object:
            return create_element("div", {"text": str(self.state.get("n", 0))})

    root = create_noop_root()
    root.render(create_element(App))

    # First update commits; cb1 runs; cb2 should be deferred.
    root.flush()
    assert log == ["cb1"]

    # Second update commits; cb2 runs now.
    root.flush()
    assert log == ["cb1", "cb2"]

