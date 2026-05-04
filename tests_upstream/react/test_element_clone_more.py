from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any

from ryact import clone_element, create_element


class _PropsWithKeyRefWarningGetters(Mapping[str, Any]):
    def __init__(self) -> None:
        self._data = {"id": "x"}

    @property
    def key(self) -> str:  # noqa: A003
        raise RuntimeError("key getter should not be accessed")

    @property
    def ref(self) -> object:  # noqa: A003
        raise RuntimeError("ref getter should not be accessed")

    def __getitem__(self, k: str) -> Any:
        return self._data[k]

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)


def test_should_ignore_key_and_ref_warning_getters() -> None:
    # Upstream: ReactElementClone-test.js
    # "should ignore key and ref warning getters"
    el = create_element("div", {"key": "k1", "ref": object()})
    out = clone_element(el, _PropsWithKeyRefWarningGetters())
    assert out.key == "k1"
    assert "id" in out.props
