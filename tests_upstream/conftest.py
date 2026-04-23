"""Expose repo `scripts/` on sys.path so tests can import scheduler_jest_extract."""

from __future__ import annotations

import sys
from pathlib import Path

_scripts = Path(__file__).resolve().parents[1] / "scripts"
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))
