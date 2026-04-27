from __future__ import annotations

from ryact import create_element


def test_int_subclass_with_iter_is_not_expanded_as_child_iterable() -> None:
    # Upstream: ReactElementValidator — #4776 (numeric children not iterable)
    class IterableInt(int):
        def __iter__(self) -> object:
            raise AssertionError("number iterator should not be used for child flattening")

    create_element(
        "div",
        None,
        IterableInt(5),
        create_element("span", {"key": "k", "text": "x"}),
    )
