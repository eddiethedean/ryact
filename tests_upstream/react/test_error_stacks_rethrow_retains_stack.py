from __future__ import annotations

import re

import pytest

from ryact import Component, create_element
from ryact_testkit import create_noop_root


def test_retains_component_stack_when_rethrowing_an_error() -> None:
    # Upstream: ReactErrorStacks-test.js —
    # "retains component and owner stacks when rethrowing an error"
    #
    # We don't model owner stacks yet; this slice asserts the component stack is preserved
    # and not duplicated when an error boundary rethrows.
    class Boundary(Component):
        def componentDidCatch(self, err: BaseException) -> None:  # noqa: N802
            raise err

        def render(self) -> object:
            children = self.props["children"]
            if isinstance(children, tuple):
                return children[0] if children else None
            return children

    def Boom(**_: object) -> object:
        raise RuntimeError("boom")

    root = create_noop_root()
    with pytest.raises(RuntimeError, match=re.escape("boom")) as exc:
        root.render(create_element(Boundary, {"children": create_element(Boom)}))

    msg = str(exc.value)
    assert msg.count("Component stack:") == 1
    assert "in Boom" in msg
    assert "in Boundary" in msg

