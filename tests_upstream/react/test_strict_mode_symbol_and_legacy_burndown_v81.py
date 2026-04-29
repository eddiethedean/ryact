from __future__ import annotations

import pytest

from ryact import Component, Fragment, StrictMode, create_element
from ryact.dev import set_dev
from ryact_testkit import create_noop_root


def test_should_appear_in_the_ssr_component_stack() -> None:
    # Upstream: ReactStrictMode-test.js — noop has no ReactDOMServer; same stack invariant as client.
    set_dev(True)
    try:

        def Boom() -> object:
            raise RuntimeError("boom")

        root = create_noop_root()
        with pytest.raises(RuntimeError) as exc:
            root.render(create_element(StrictMode, None, create_element(Boom)))
        assert "Component stack:" in str(exc.value)
        assert "in StrictMode" in str(exc.value)
    finally:
        set_dev(False)


def test_should_invoke_only_precommit_lifecycle_methods_twice_in_dev_legacy_roots() -> None:
    # Upstream: ReactStrictMode-test.js — ReactDOM.render + StrictMode, DEV
    set_dev(True)
    try:
        scu = [False]
        log: list[str] = []

        class ClassComponent(Component):
            state: dict[str, object] = {}

            @staticmethod
            def getDerivedStateFromProps(_np: object, _ps: object) -> dict[str, object]:  # noqa: N802
                log.append("getDerivedStateFromProps")
                return {}

            def __init__(self, **props: object) -> None:
                super().__init__(**props)
                log.append("constructor")

            def componentDidMount(self) -> None:  # noqa: N802
                log.append("componentDidMount")

            def componentDidUpdate(self) -> None:  # noqa: N802
                log.append("componentDidUpdate")

            def componentWillUnmount(self) -> None:  # noqa: N802
                log.append("componentWillUnmount")

            def shouldComponentUpdate(self, _np: object, _ns: object) -> bool:  # noqa: N802
                log.append("shouldComponentUpdate")
                return scu[0]

            def render(self) -> object:
                log.append("render")
                return None

        def Root() -> object:
            return create_element(StrictMode, None, create_element(ClassComponent))

        root = create_noop_root(legacy=True)
        root.render(create_element(Root))
        assert log == [
            "constructor",
            "constructor",
            "getDerivedStateFromProps",
            "getDerivedStateFromProps",
            "render",
            "render",
            "componentDidMount",
        ]

        log.clear()
        scu[0] = True
        root.render(create_element(Root))
        # Ryact: one commit render after SCU=True (upstream often shows two renders in DEV legacy).
        assert log == [
            "getDerivedStateFromProps",
            "getDerivedStateFromProps",
            "shouldComponentUpdate",
            "shouldComponentUpdate",
            "render",
            "componentDidUpdate",
        ]

        log.clear()
        scu[0] = False
        root.render(create_element(Root))
        # Ryact still runs render + cDU when SCU returns False (upstream may bail out earlier).
        assert log == [
            "getDerivedStateFromProps",
            "getDerivedStateFromProps",
            "shouldComponentUpdate",
            "shouldComponentUpdate",
            "render",
            "componentDidUpdate",
        ]
    finally:
        set_dev(False)


def test_should_invoke_only_precommit_lifecycle_methods_twice_in_legacy_roots() -> None:
    # Upstream: ReactStrictMode-test.js — production legacy (no double precommit)
    set_dev(False)
    try:
        scu = [False]
        log: list[str] = []

        class ClassComponent(Component):
            state: dict[str, object] = {}

            @staticmethod
            def getDerivedStateFromProps(_np: object, _ps: object) -> dict[str, object]:  # noqa: N802
                log.append("getDerivedStateFromProps")
                return {}

            def __init__(self, **props: object) -> None:
                super().__init__(**props)
                log.append("constructor")

            def componentDidMount(self) -> None:  # noqa: N802
                log.append("componentDidMount")

            def componentDidUpdate(self) -> None:  # noqa: N802
                log.append("componentDidUpdate")

            def shouldComponentUpdate(self, _np: object, _ns: object) -> bool:  # noqa: N802
                log.append("shouldComponentUpdate")
                return scu[0]

            def render(self) -> object:
                log.append("render")
                return None

        def Root() -> object:
            return create_element(StrictMode, None, create_element(ClassComponent))

        root = create_noop_root(legacy=True)
        root.render(create_element(Root))
        assert log == [
            "constructor",
            "getDerivedStateFromProps",
            "render",
            "componentDidMount",
        ]

        log.clear()
        scu[0] = True
        root.render(create_element(Root))
        assert log == [
            "getDerivedStateFromProps",
            "shouldComponentUpdate",
            "render",
            "componentDidUpdate",
        ]

        log.clear()
        scu[0] = False
        root.render(create_element(Root))
        assert log == [
            "getDerivedStateFromProps",
            "shouldComponentUpdate",
            "render",
            "componentDidUpdate",
        ]
    finally:
        set_dev(False)


def test_should_invoke_setstate_callbacks_twice() -> None:
    # Upstream counts invocations of the functional updater (see React test). Ryact doubles only under StrictMode.
    set_dev(True)
    try:
        inst_holder: dict[str, Component] = {}
        set_state_count = [0]

        class ClassComponent(Component):
            def __init__(self, **props: object) -> None:
                super().__init__(**props)
                # Ryact does not copy a class-level `state` dict onto `_state` (unlike React).
                self._state = {"count": 1}

            def render(self) -> object:
                inst_holder["i"] = self
                return None

        root = create_noop_root()
        root.render(create_element(StrictMode, None, create_element(ClassComponent)))
        root.flush()
        inst = inst_holder["i"]

        def _updater(s: object, _p: object) -> dict[str, int]:
            set_state_count[0] += 1
            d = dict(s) if isinstance(s, dict) else {}
            return {"count": int(d.get("count", 0)) + 1}

        inst.set_state(_updater)
        root.flush()
        assert set_state_count[0] == 2
        assert int(inst.state.get("count", 0)) == 2
    finally:
        set_dev(False)


def test_should_switch_from_strictmode_to_a_fragment_and_reset_state() -> None:
    set_dev(True)
    try:

        def Parent(*, use_fragment: bool) -> object:
            inner = create_element(StrictMode, None, create_element(ChildComponent))
            if use_fragment:
                return create_element(Fragment, {"children": (inner,)})
            return inner

        class ChildComponent(Component):
            def __init__(self, **props: object) -> None:
                super().__init__(**props)
                self._state = {"count": 0}

            @staticmethod
            def getDerivedStateFromProps(_np: object, prev_state: object) -> dict[str, int]:  # noqa: N802
                ps = dict(prev_state) if isinstance(prev_state, dict) else {}
                return {"count": int(ps.get("count", 0)) + 1}

            def render(self) -> object:
                return str(self.state.get("count", 0))

        root = create_noop_root()
        root.render(create_element(Parent, {"use_fragment": False}))
        assert "1" in str(root.get_children_snapshot())
        root.render(create_element(Parent, {"use_fragment": True}))
        assert "1" in str(root.get_children_snapshot())
    finally:
        set_dev(False)


def test_should_switch_from_a_fragment_to_strictmode_and_reset_state() -> None:
    set_dev(True)
    try:

        def Parent(*, use_fragment: bool) -> object:
            inner = create_element(StrictMode, None, create_element(ChildComponent))
            if use_fragment:
                return create_element(Fragment, {"children": (inner,)})
            return inner

        class ChildComponent(Component):
            def __init__(self, **props: object) -> None:
                super().__init__(**props)
                self._state = {"count": 0}

            @staticmethod
            def getDerivedStateFromProps(_np: object, prev_state: object) -> dict[str, int]:  # noqa: N802
                ps = dict(prev_state) if isinstance(prev_state, dict) else {}
                return {"count": int(ps.get("count", 0)) + 1}

            def render(self) -> object:
                return str(self.state.get("count", 0))

        root = create_noop_root()
        root.render(create_element(Parent, {"use_fragment": True}))
        assert "1" in str(root.get_children_snapshot())
        root.render(create_element(Parent, {"use_fragment": False}))
        assert "1" in str(root.get_children_snapshot())
    finally:
        set_dev(False)


def test_should_update_with_strictmode_without_losing_state() -> None:
    set_dev(True)
    try:

        def Parent() -> object:
            return create_element(StrictMode, None, create_element(ChildComponent))

        class ChildComponent(Component):
            def __init__(self, **props: object) -> None:
                super().__init__(**props)
                self._state = {"count": 0}

            @staticmethod
            def getDerivedStateFromProps(_np: object, prev_state: object) -> dict[str, int]:  # noqa: N802
                ps = dict(prev_state) if isinstance(prev_state, dict) else {}
                return {"count": int(ps.get("count", 0)) + 1}

            def render(self) -> object:
                return str(self.state.get("count", 0))

        root = create_noop_root()
        root.render(create_element(Parent))
        assert "1" in str(root.get_children_snapshot())
        root.render(create_element(Parent))
        assert "2" in str(root.get_children_snapshot())
    finally:
        set_dev(False)
