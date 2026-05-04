from __future__ import annotations

from typing import Any

import pytest

from ryact import create_element
from ryact_testkit import create_noop_root


def test_component_stack_includes_created_by_owner() -> None:
    def Child() -> Any:
        raise RuntimeError("boom")

    def Parent() -> Any:
        return create_element(Child)

    root = create_noop_root()
    with pytest.raises(RuntimeError) as ei:
        root.render(create_element(Parent))
        root.flush()
    msg = str(ei.value)
    assert "Component stack:" in msg
    assert "Child (created by Parent)" in msg

