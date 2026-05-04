from __future__ import annotations

from typing import Any

import pytest

from ryact import create_element
from ryact_testkit import create_noop_root


def test_noop_root_allows_custom_uncaught_error_reporter() -> None:
    seen: list[str] = []

    def App() -> Any:
        raise RuntimeError("boom")

    root = create_noop_root()

    def reporter(err: BaseException) -> None:
        seen.append(str(err))

    root.container.uncaught_error_reporter = reporter
    with pytest.raises(RuntimeError):
        root.render(create_element(App))
        root.flush()
    assert any("boom" in s for s in seen)

