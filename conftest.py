"""Repo-wide pytest hooks shared by all ``testpaths`` (including xdist workers)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest


@pytest.fixture(autouse=True)
def ensure_greenlet_context() -> Iterator[None]:
    """
    Shadow third-party async ``ensure_greenlet_context`` autouse fixtures.

    Without this at the repo root, ``tests_property`` / ``tests_jsx`` / etc. pick up an
    async fixture from the environment and fail under pytest-asyncio / pytest 9.
    """
    yield
