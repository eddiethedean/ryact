from __future__ import annotations


class EsbuildNotFoundError(RuntimeError):
    """Raised when neither local `esbuild` nor `npx` is available."""
