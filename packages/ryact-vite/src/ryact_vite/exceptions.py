from __future__ import annotations


class ViteNotFoundError(RuntimeError):
    """Raised when neither local `vite` nor `npx` is available."""
