from __future__ import annotations

from collections.abc import Callable

from ryact import StrictMode, create_element, use_effect, use_ref, use_state
from ryact.concurrent import Suspend, Thenable, suspense
from ryact.dev import set_dev
from ryact_testkit import create_noop_root


def test_should_double_invoke_effects_after_a_re_suspend() -> None:
    # Upstream: StrictEffectsMode-test.js (react/main) — @gate __DEV__
    set_dev(True)
    try:
        log: list[str] = []
        should_suspend = {"v": True}
        t = Thenable()

        def Fallback() -> object:
            log.append("Fallback")
            return "Loading"

        def Parent(*, prop: str) -> object:
            log.append("Parent rendered")

            def eff() -> Callable[[], None]:
                log.append("Parent create")

                def cleanup() -> None:
                    log.append("Parent destroy")

                return cleanup

            def eff_dep() -> Callable[[], None]:
                log.append("Parent dep create")

                def cleanup() -> None:
                    log.append("Parent dep destroy")

                return cleanup

            use_effect(eff, ())
            use_effect(eff_dep, (prop,))

            return suspense(
                fallback=create_element(Fallback),
                children=create_element(Child, {"prop": prop}),
            )

        def Child(*, prop: str) -> object:
            count, set_count = use_state(0)
            ref = use_ref(None)
            log.append("Child rendered")

            def eff() -> Callable[[], None]:
                log.append("Child create")

                def cleanup() -> None:
                    log.append("Child destroy")
                    ref["current"] = True

                return cleanup

            use_effect(eff, ())

            key = f"{prop}-{count}"

            def eff_dep() -> Callable[[], None] | None:
                log.append("Child dep create")
                if ref["current"] is True:
                    ref["current"] = False
                    set_count(lambda c: c + 1)
                    log.append("-----------------------after setState")
                    return None

                def cleanup() -> None:
                    log.append("Child dep destroy")

                return cleanup

            use_effect(eff_dep, (key,))

            if should_suspend["v"]:
                log.append("Child suspended")
                raise Suspend(t)
            return None

        root = create_noop_root()

        # Initial mount (not suspended)
        should_suspend["v"] = False
        root.render(create_element(StrictMode, None, create_element(Parent, {"prop": "A"})))
        # The strict replay sequence may enqueue a sync update during commit. Drain it
        # so subsequent renders don't flush multiple queued updates.
        root.flush()

        # Now re-suspend
        should_suspend["v"] = True
        log.clear()
        root.render(create_element(StrictMode, None, create_element(Parent, {"prop": "A"})))
        assert log == [
            "Parent rendered",
            "Child rendered",
            "Child suspended",
            "Fallback",
            "Fallback",
            # pre-warming
            "Child rendered",
            "Child suspended",
        ]

        # While suspended, update prop
        log.clear()
        root.render(create_element(StrictMode, None, create_element(Parent, {"prop": "B"})))
        assert log == [
            "Parent rendered",
            "Child rendered",
            "Child suspended",
            "Fallback",
            "Fallback",
            # pre-warming
            "Child rendered",
            "Child suspended",
            "Parent dep destroy",
            "Parent dep create",
        ]

        # Resolve and commit
        log.clear()
        t.resolve()
        should_suspend["v"] = False
        root.flush()

        assert log == [
            "Parent rendered",
            "Child rendered",
            "Child rendered",
            "Child destroy",
            "Child dep destroy",
            "Child create",
            "Child dep create",
            "Child destroy",
            "Child dep destroy",
            "Child create",
            "Child dep create",
            "-----------------------after setState",
            "Parent rendered",
            "Child rendered",
            "Child dep create",
        ]
    finally:
        set_dev(False)

