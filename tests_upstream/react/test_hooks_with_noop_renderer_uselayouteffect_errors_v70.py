from __future__ import annotations

from typing import Any

import pytest
from ryact import create_element, use_layout_effect
from ryact_testkit import create_noop_root


def test_catches_errors_thrown_in_uselayouteffect() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "catches errors thrown in useLayoutEffect"
    root = create_noop_root()

    def App() -> Any:
        def eff() -> Any:
            raise RuntimeError("layout boom")

        use_layout_effect(eff, ())
        return create_element("span", {"text": "ok"})

    with pytest.raises(RuntimeError, match="layout boom"):
        root.render(create_element(App))
