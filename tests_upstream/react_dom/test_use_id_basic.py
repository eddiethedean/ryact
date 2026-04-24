from __future__ import annotations

from ryact import StrictMode, create_element, use_id
from ryact.dev import set_dev
from ryact_testkit import create_noop_root


def test_useid_basic_example() -> None:
    # Upstream: ReactDOMUseId-test.js
    # "basic example"
    root = create_noop_root()

    def Child() -> object:
        return create_element("div", {"id": use_id()})

    def App() -> object:
        return create_element(
            "parent",
            None,
            create_element(Child),
            create_element(Child),
        )

    root.render(create_element(App))
    committed1 = root.container.last_committed
    assert committed1 is not None
    ids1 = [c["props"]["id"] for c in committed1["children"]]
    assert ids1[0] != ids1[1]

    root.render(create_element(App))
    committed2 = root.container.last_committed
    assert committed2 is not None
    ids2 = [c["props"]["id"] for c in committed2["children"]]
    assert ids2 == ids1


def test_useid_does_not_forget_mounted_id_in_dev() -> None:
    # Upstream: ReactDOMUseId-test.js
    # "does not forget it mounted an id when re-rendering in dev"
    set_dev(True)
    root = create_noop_root()

    def App() -> object:
        return create_element("div", {"id": use_id()})

    root.render(create_element(StrictMode, None, create_element(App)))
    committed1 = root.container.last_committed
    assert committed1 is not None
    id1 = committed1["props"]["id"]

    root.render(create_element(StrictMode, None, create_element(App)))
    committed2 = root.container.last_committed
    assert committed2 is not None
    id2 = committed2["props"]["id"]
    assert id2 == id1
