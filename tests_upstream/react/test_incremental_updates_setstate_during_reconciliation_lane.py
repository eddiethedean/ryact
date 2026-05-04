from __future__ import annotations

from ryact import Component, create_element
from ryact.concurrent import start_transition
from ryact.reconciler import TRANSITION_LANE
from ryact_testkit import create_noop_root


def test_setstate_during_reconciliation_inherits_current_lane() -> None:
    # Upstream: ReactIncrementalUpdates-test.js —
    # "gives setState during reconciliation the same priority as whatever level is currently reconciling"
    inst: App | None = None

    class App(Component):
        def __init__(self) -> None:
            super().__init__()
            nonlocal inst
            inst = self
            self._did_schedule = False

        def componentDidMount(self) -> None:
            start_transition(lambda: self.set_state({"step": 1}))

        def render(self) -> object:
            if self.state.get("step", 0) == 1 and not self._did_schedule:
                self._did_schedule = True
                self.set_state({"inner": True})
            return create_element("div", {"text": "ok"})

    root = create_noop_root()
    root.render(create_element(App))
    assert inst is not None

    root.flush()  # commit transition step=1
    pending = getattr(inst, "_pending_state_updates", None)
    assert isinstance(pending, list) and pending
    lane = pending[0][0]
    assert lane is TRANSITION_LANE
