"""Re-export legacy mount/render API (``ReactDOM.render`` subset)."""

from __future__ import annotations

from .legacy_mount import legacy_render

__all__ = ["legacy_render"]
