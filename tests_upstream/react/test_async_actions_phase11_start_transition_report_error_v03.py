from __future__ import annotations

from typing import Any

import pytest
from ryact import start_transition
from ryact.concurrent import Thenable, set_report_error


def test_react_starttransition_captures_sync_errors_and_passes_them_to_reporterror() -> None:
    # Upstream: ReactAsyncActions-test.js
    # "React.startTransition captures sync errors and passes them to reportError"
    errors: list[str] = []
    set_report_error(lambda e: errors.append(str(e)))
    try:
        with pytest.raises(RuntimeError, match="boom"):
            start_transition(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        assert errors == ["boom"]
    finally:
        set_report_error(None)


def test_react_starttransition_captures_async_errors_and_passes_them_to_reporterror() -> None:
    # Upstream: ReactAsyncActions-test.js
    # "React.startTransition captures async errors and passes them to reportError"
    errors: list[str] = []
    set_report_error(lambda e: errors.append(str(e)))
    try:
        t = Thenable()

        def action() -> Any:
            return t

        start_transition(action)
        t.reject(RuntimeError("async boom"))
        assert errors == ["async boom"]
    finally:
        set_report_error(None)
