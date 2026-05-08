from __future__ import annotations

import re

_VALID_HOST_TAG_RE = re.compile(r"^[A-Za-z][A-Za-z0-9:_-]*$")


def validate_host_intrinsic_tag_name(tag: str) -> None:
    """Reject invalid / injection-prone intrinsic tag names (client + SSR shared)."""

    if not _VALID_HOST_TAG_RE.match(tag):
        raise ValueError(f"Invalid tag name: {tag!r}")
    lowered = tag.lower()
    if lowered.startswith("script") and "<" in lowered:
        raise ValueError(f"Invalid tag name: {tag!r}")
