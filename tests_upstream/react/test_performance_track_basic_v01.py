from __future__ import annotations

from ryact.devtools import performance_track_diff_hint


def test_performance_track_diff_hint_surface_exists() -> None:
    out = performance_track_diff_hint({"a": 1}, {"a": 2})
    assert isinstance(out, list)

