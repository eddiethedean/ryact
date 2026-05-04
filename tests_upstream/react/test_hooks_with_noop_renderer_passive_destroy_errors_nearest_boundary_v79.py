from __future__ import annotations

from typing import Any

import pytest
from ryact import Component, create_element, use_effect, use_state
from ryact_testkit import act, create_noop_root, set_act_environment_enabled


@pytest.mark.asyncio
async def test_should_call_gdsfe_in_nearest_still_mounted_boundary() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "should call getDerivedStateFromError in the nearest still-mounted boundary"
    log: list[str] = []

    class Boundary(Component):
        @staticmethod
        def getDerivedStateFromError(_err: BaseException) -> dict[str, Any]:
            log.append("gdsfe")
            return {"hasError": True}

        def __init__(self, **props: Any) -> None:
            super().__init__(**props)
            self._state = {"hasError": False}

        def render(self) -> Any:
            if self.state.get("hasError"):
                return create_element("span", {"text": "fallback"})
            return self.props["children"]

    def Boom() -> Any:
        def eff() -> Any:
            def destroy() -> None:
                raise RuntimeError("boom")

            return destroy

        use_effect(eff, ())
        return create_element("span", {"text": "boom"})

    def App() -> Any:
        show, set_show = use_state(True)

        def eff() -> Any:
            set_show(False)
            return None

        use_effect(eff, ())
        return create_element(Boundary, {"children": create_element(Boom) if show else None})

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App))
        # Pending passive destroy runs on the next flush and should be captured by Boundary.
        root.flush()
        assert log == ["gdsfe"]
        assert "fallback" in str(root.get_children_snapshot())
    finally:
        set_act_environment_enabled(False)


@pytest.mark.asyncio
async def test_should_rethrow_if_no_still_mounted_boundaries() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "should rethrow error if there are no still-mounted boundaries"
    def Boom() -> Any:
        def eff() -> Any:
            def destroy() -> None:
                raise RuntimeError("boom")

            return destroy

        use_effect(eff, ())
        return create_element("span", {"text": "boom"})

    def App() -> Any:
        show, set_show = use_state(True)

        def eff() -> Any:
            set_show(False)
            return None

        use_effect(eff, ())
        return create_element(Boom) if show else None

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App))
        with pytest.raises(RuntimeError, match="boom"):
            root.flush()
    finally:
        set_act_environment_enabled(False)


@pytest.mark.asyncio
async def test_should_skip_unmounted_boundaries_and_use_nearest_still_mounted_boundary() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "should skip unmounted boundaries and use the nearest still-mounted boundary"
    log: list[str] = []

    class Outer(Component):
        @staticmethod
        def getDerivedStateFromError(_err: BaseException) -> dict[str, Any]:
            log.append("outer")
            return {"hasError": True}

        def __init__(self, **props: Any) -> None:
            super().__init__(**props)
            self._state = {"hasError": False}

        def render(self) -> Any:
            if self.state.get("hasError"):
                return create_element("span", {"text": "outer fallback"})
            return self.props["children"]

    class Inner(Component):
        @staticmethod
        def getDerivedStateFromError(_err: BaseException) -> dict[str, Any]:
            log.append("inner")
            return {"hasError": True}

        def __init__(self, **props: Any) -> None:
            super().__init__(**props)
            self._state = {"hasError": False}

        def render(self) -> Any:
            if self.state.get("hasError"):
                return create_element("span", {"text": "inner fallback"})
            return self.props["children"]

    def Boom() -> Any:
        def eff() -> Any:
            def destroy() -> None:
                raise RuntimeError("boom")

            return destroy

        use_effect(eff, ())
        return create_element("span", {"text": "boom"})

    def App() -> Any:
        show_inner, set_show_inner = use_state(True)

        def eff() -> Any:
            set_show_inner(False)
            return None

        use_effect(eff, ())
        return create_element(
            Outer,
            {"children": create_element(Inner, {"children": create_element(Boom)}) if show_inner else None},
        )

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App))
        root.flush()
        assert log == ["outer"]
        assert "outer fallback" in str(root.get_children_snapshot())
    finally:
        set_act_environment_enabled(False)


@pytest.mark.asyncio
async def test_should_use_nearest_still_mounted_boundary_when_all_mounted() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "should use the nearest still-mounted boundary if there are no unmounted boundaries"
    log: list[str] = []

    class Outer(Component):
        @staticmethod
        def getDerivedStateFromError(_err: BaseException) -> dict[str, Any]:
            log.append("outer")
            return {"hasError": True}

        def __init__(self, **props: Any) -> None:
            super().__init__(**props)
            self._state = {"hasError": False}

        def render(self) -> Any:
            if self.state.get("hasError"):
                return create_element("span", {"text": "outer fallback"})
            return self.props["children"]

    class Inner(Component):
        @staticmethod
        def getDerivedStateFromError(_err: BaseException) -> dict[str, Any]:
            log.append("inner")
            return {"hasError": True}

        def __init__(self, **props: Any) -> None:
            super().__init__(**props)
            self._state = {"hasError": False}

        def render(self) -> Any:
            if self.state.get("hasError"):
                return create_element("span", {"text": "inner fallback"})
            return self.props["children"]

    def Boom() -> Any:
        def eff() -> Any:
            def destroy() -> None:
                raise RuntimeError("boom")

            return destroy

        use_effect(eff, ())
        return create_element("span", {"text": "boom"})

    def App() -> Any:
        show_boom, set_show_boom = use_state(True)

        def eff() -> Any:
            set_show_boom(False)
            return None

        use_effect(eff, ())
        return create_element(
            Outer,
            {
                "children": create_element(
                    Inner,
                    {"children": create_element(Boom) if show_boom else None},
                )
            },
        )

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App))
        root.flush()
        assert log == ["inner"]
        assert "inner fallback" in str(root.get_children_snapshot())
    finally:
        set_act_environment_enabled(False)
