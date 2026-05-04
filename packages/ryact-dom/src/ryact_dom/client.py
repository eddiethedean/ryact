from __future__ import annotations

from ._version_check import check_versions as _check_versions

_check_versions()

from .root import create_root, hydrate_root  # noqa: E402

__all__ = ["create_root", "hydrate_root"]

