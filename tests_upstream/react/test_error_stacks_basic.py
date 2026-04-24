from __future__ import annotations

import re

import pytest
from ryact import create_element
from ryact_testkit import create_noop_root


def test_error_in_component_includes_component_stack() -> None:
    # Upstream: ReactErrorStacks-test.js
    # Minimal slice: errors should include a deterministic component stack.

    def Boom(**_: object) -> object:
        raise RuntimeError("boom")

    root = create_noop_root()
    with pytest.raises(RuntimeError, match=re.escape("boom")) as exc:
        root.render(create_element(Boom, None))

    msg = str(exc.value)
    assert "Component stack:" in msg
    assert "in Boom" in msg
