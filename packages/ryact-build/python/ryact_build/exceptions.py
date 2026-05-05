from __future__ import annotations


class NativeExtensionUnavailableError(RuntimeError):
    """Raised when the Rolldown native extension (`ryact_build._native`) is missing or failed to load."""
