from __future__ import annotations

from ryact import create_element
from ryact.hooks import use_effect, use_layout_effect
from ryact_testkit import create_noop_root


def test_layout_unmounts_on_deletion_are_fired_in_parent_child_order() -> None:
    # Upstream: ReactEffectOrdering-test.js
    log: list[str] = []

    def Child() -> object:
        use_layout_effect(lambda: (lambda: log.append("layout-unmount:child")))
        return create_element("div", {"text": "child"})

    def Parent() -> object:
        use_layout_effect(lambda: (lambda: log.append("layout-unmount:parent")))
        return create_element("div", {"text": "parent"}, create_element(Child))

    root = create_noop_root()
    root.render(create_element(Parent))
    log.clear()
    root.render(None)

    assert log == ["layout-unmount:parent", "layout-unmount:child"]


def test_passive_unmounts_on_deletion_are_fired_in_parent_child_order() -> None:
    # Upstream: ReactEffectOrdering-test.js
    log: list[str] = []

    def Child() -> object:
        use_effect(lambda: (lambda: log.append("passive-unmount:child")))
        return create_element("div", {"text": "child"})

    def Parent() -> object:
        use_effect(lambda: (lambda: log.append("passive-unmount:parent")))
        return create_element("div", {"text": "parent"}, create_element(Child))

    root = create_noop_root()
    root.render(create_element(Parent))
    log.clear()
    root.render(None)

    assert log == ["passive-unmount:parent", "passive-unmount:child"]

