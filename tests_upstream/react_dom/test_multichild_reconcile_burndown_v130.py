"""ReactMultiChildReconcile-test.js parity: keyed child order, null slots, iterables (v130)."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Mapping
from typing import Any

from ryact import create_element
from ryact_dom.dom import Container, ElementNode, TextNode
from ryact_dom.root import create_root


def _status(user: str, status: str) -> object:
    return create_element("span", {"key": user, "data-user": user}, status)


def _prepare_array(children: list[object]) -> list[object]:
    return children


class _LegacyChildIterable:
    """Minimal ``{ '@@iterator': fn }`` child container (React legacy iterable)."""

    def __init__(self, items: list[object]) -> None:
        self._items = items

    def __iter__(self) -> Iterator[object]:
        yield from self._items


def _prepare_legacy_iterable(children: list[object]) -> _LegacyChildIterable:
    return _LegacyChildIterable(children)


def _prepare_modern_iterable(children: list[object]) -> Iterable[object]:
    return iter(children)


def _friends(
    username_to_status: Mapping[str, str | None] | None,
    *,
    prepare: Callable[[list[object]], object] = _prepare_array,
) -> object:
    uts: dict[str, str | None] = dict(username_to_status or {})
    kids: list[object] = []
    for username in uts:
        status = uts[username]
        kids.append(None if not status else _status(username, status))
    prepared = prepare(kids)
    if isinstance(prepared, (list, tuple)):
        ch: tuple[object, ...] = tuple(prepared)
    else:
        ch = tuple(prepared)
    return create_element("div", None, *ch)


def _div(c: Container) -> ElementNode:
    root_child = c.root.children[0]
    assert isinstance(root_child, ElementNode)
    return root_child


def _displays(div: ElementNode) -> dict[str, ElementNode]:
    out: dict[str, ElementNode] = {}
    for ch in div.children:
        if isinstance(ch, ElementNode):
            user = ch.props.get("data-user")
            if user is not None:
                out[str(user)] = ch
    return out


def _status_text(node: ElementNode) -> str:
    if node.children:
        t = node.children[0]
        if isinstance(t, TextNode):
            return t.text
    return ""


def _dom_user_order(div: ElementNode) -> list[str]:
    return [str(ch.props["data-user"]) for ch in div.children if isinstance(ch, ElementNode)]


def _verify_statuses(displays: dict[str, ElementNode], uts: Mapping[str, str | None]) -> None:
    expected = {k: v for k, v in uts.items() if v}
    assert set(displays.keys()) == set(expected.keys())
    for user, status in expected.items():
        assert _status_text(displays[user]) == status


def _verify_order(div: ElementNode, uts: Mapping[str, str | None]) -> None:
    expected_users = [k for k, v in uts.items() if v]
    assert _dom_user_order(div) == expected_users


def _verify_states_preserved(
    last_ids: dict[str, int],
    displays: dict[str, ElementNode],
) -> None:
    for user, node in displays.items():
        if user in last_ids:
            assert node._host_reconcile_id == last_ids[user]


def _run_sequence(
    sequence: list[Mapping[str, str | None] | dict[str, Any]],
    *,
    prepare: Callable[[list[object]], object] = _prepare_array,
) -> None:
    c = Container()
    r = create_root(c)
    last_ids: dict[str, int] = {}
    for i, step in enumerate(sequence):
        uts = step.get("usernameToStatus", {})
        r.render(_friends(uts, prepare=prepare))
        div = _div(c)
        displays = _displays(div)
        _verify_statuses(displays, uts)
        _verify_order(div, uts)
        if i > 0:
            _verify_states_preserved(last_ids, displays)
        last_ids = {u: n._host_reconcile_id for u, n in displays.items()}


def test_should_reset_internal_state_if_removed_then_readded_in_an_array() -> None:
    c = Container()
    r = create_root(c)
    r.render(_friends({"jcw": "jcwStatus"}))
    div = _div(c)
    displays = _displays(div)
    start_id = displays["jcw"]._host_reconcile_id

    r.render(_friends({}))
    assert "jcw" not in _displays(_div(c))

    r.render(_friends({"jcw": "jcwStatus"}))
    displays2 = _displays(_div(c))
    assert displays2["jcw"]._host_reconcile_id != start_id


def test_should_reset_internal_state_if_removed_then_readded_in_a_legacy_iterable() -> None:
    c = Container()
    r = create_root(c)
    r.render(_friends({"jcw": "jcwStatus"}, prepare=_prepare_legacy_iterable))
    start_id = _displays(_div(c))["jcw"]._host_reconcile_id
    r.render(_friends({}, prepare=_prepare_legacy_iterable))
    assert "jcw" not in _displays(_div(c))
    r.render(_friends({"jcw": "jcwStatus"}, prepare=_prepare_legacy_iterable))
    assert _displays(_div(c))["jcw"]._host_reconcile_id != start_id


def test_should_reset_internal_state_if_removed_then_readded_in_a_modern_iterable() -> None:
    c = Container()
    r = create_root(c)
    r.render(_friends({"jcw": "jcwStatus"}, prepare=_prepare_modern_iterable))
    start_id = _displays(_div(c))["jcw"]._host_reconcile_id
    r.render(_friends({}, prepare=_prepare_modern_iterable))
    assert "jcw" not in _displays(_div(c))
    r.render(_friends({"jcw": "jcwStatus"}, prepare=_prepare_modern_iterable))
    assert _displays(_div(c))["jcw"]._host_reconcile_id != start_id


def test_should_create_unique_identity() -> None:
    uts = {"jcw": "jcwStatus", "awalke": "awalkeStatus", "bob": "bobStatus"}
    c = Container()
    r = create_root(c)
    r.render(_friends(uts))
    displays = _displays(_div(c))
    ids = {n._host_reconcile_id for n in displays.values()}
    assert len(ids) == 3


def test_should_preserve_order_if_children_order_has_not_changed() -> None:
    _run_sequence(
        [
            {"usernameToStatus": {"jcw": "jcwStatus", "jordanjcw": "jordanjcwStatus"}},
            {"usernameToStatus": {"jcw": "jcwstatus2", "jordanjcw": "jordanjcwstatus2"}},
        ],
    )


def test_should_transition_from_zero_to_one_children_correctly() -> None:
    _run_sequence(
        [
            {"usernameToStatus": {}},
            {"usernameToStatus": {"first": "firstStatus"}},
        ],
    )


def test_should_transition_from_one_to_zero_children_correctly() -> None:
    _run_sequence(
        [
            {"usernameToStatus": {"first": "firstStatus"}},
            {"usernameToStatus": {}},
        ],
    )


def test_should_transition_from_one_child_to_null_children() -> None:
    _run_sequence(
        [
            {"usernameToStatus": {"first": "firstStatus"}},
            {},
        ],
    )


def test_should_transition_from_null_children_to_one_child() -> None:
    _run_sequence(
        [
            {},
            {"usernameToStatus": {"first": "firstStatus"}},
        ],
    )


def test_should_transition_from_zero_children_to_null_children() -> None:
    _run_sequence(
        [
            {"usernameToStatus": {}},
            {},
        ],
    )


def test_should_transition_from_null_children_to_zero_children() -> None:
    _run_sequence(
        [
            {},
            {"usernameToStatus": {}},
        ],
    )


def test_should_remove_nulled_out_children_at_the_beginning() -> None:
    _run_sequence(
        [
            {"usernameToStatus": {"jcw": "jcwStatus", "jordanjcw": "jordanjcwStatus"}},
            {"usernameToStatus": {"jcw": None, "jordanjcw": "jordanjcwstatus2"}},
        ],
    )


def test_should_remove_nulled_out_children_at_the_end() -> None:
    _run_sequence(
        [
            {"usernameToStatus": {"jcw": "jcwStatus", "jordanjcw": "jordanjcwStatus"}},
            {"usernameToStatus": {"jcw": "jcwstatus2", "jordanjcw": None}},
        ],
    )


def test_should_reverse_the_order_of_two_children() -> None:
    _run_sequence(
        [
            {"usernameToStatus": {"userOne": "userOneStatus", "userTwo": "userTwoStatus"}},
            {"usernameToStatus": {"userTwo": "userTwoStatus", "userOne": "userOneStatus"}},
        ],
    )


def test_should_reverse_the_order_of_more_than_two_children() -> None:
    _run_sequence(
        [
            {
                "usernameToStatus": {
                    "userOne": "userOneStatus",
                    "userTwo": "userTwoStatus",
                    "userThree": "userThreeStatus",
                },
            },
            {
                "usernameToStatus": {
                    "userThree": "userThreeStatus",
                    "userTwo": "userTwoStatus",
                    "userOne": "userOneStatus",
                },
            },
        ],
    )


def test_should_cycle_order_correctly() -> None:
    _run_sequence(
        [
            {
                "usernameToStatus": {
                    "userOne": "userOneStatus",
                    "userTwo": "userTwoStatus",
                    "userThree": "userThreeStatus",
                    "userFour": "userFourStatus",
                },
            },
            {
                "usernameToStatus": {
                    "userTwo": "userTwoStatus",
                    "userThree": "userThreeStatus",
                    "userFour": "userFourStatus",
                    "userOne": "userOneStatus",
                },
            },
            {
                "usernameToStatus": {
                    "userThree": "userThreeStatus",
                    "userFour": "userFourStatus",
                    "userOne": "userOneStatus",
                    "userTwo": "userTwoStatus",
                },
            },
            {
                "usernameToStatus": {
                    "userFour": "userFourStatus",
                    "userOne": "userOneStatus",
                    "userTwo": "userTwoStatus",
                    "userThree": "userThreeStatus",
                },
            },
            {
                "usernameToStatus": {
                    "userOne": "userOneStatus",
                    "userTwo": "userTwoStatus",
                    "userThree": "userThreeStatus",
                    "userFour": "userFourStatus",
                },
            },
        ],
    )


def test_should_cycle_order_correctly_in_the_other_direction() -> None:
    _run_sequence(
        [
            {
                "usernameToStatus": {
                    "userOne": "userOneStatus",
                    "userTwo": "userTwoStatus",
                    "userThree": "userThreeStatus",
                    "userFour": "userFourStatus",
                },
            },
            {
                "usernameToStatus": {
                    "userFour": "userFourStatus",
                    "userOne": "userOneStatus",
                    "userTwo": "userTwoStatus",
                    "userThree": "userThreeStatus",
                },
            },
            {
                "usernameToStatus": {
                    "userThree": "userThreeStatus",
                    "userFour": "userFourStatus",
                    "userOne": "userOneStatus",
                    "userTwo": "userTwoStatus",
                },
            },
            {
                "usernameToStatus": {
                    "userTwo": "userTwoStatus",
                    "userThree": "userThreeStatus",
                    "userFour": "userFourStatus",
                    "userOne": "userOneStatus",
                },
            },
            {
                "usernameToStatus": {
                    "userOne": "userOneStatus",
                    "userTwo": "userTwoStatus",
                    "userThree": "userThreeStatus",
                    "userFour": "userFourStatus",
                },
            },
        ],
    )


def test_should_remove_nulled_out_children_and_ignore_new_null_children() -> None:
    _run_sequence(
        [
            {"usernameToStatus": {"jcw": "jcwStatus", "jordanjcw": "jordanjcwStatus"}},
            {
                "usernameToStatus": {
                    "jordanjcw": "jordanjcwstatus2",
                    "jcw": None,
                    "another": None,
                },
            },
        ],
    )


def test_should_remove_nulled_out_children_and_reorder_remaining() -> None:
    _run_sequence(
        [
            {
                "usernameToStatus": {
                    "jcw": "jcwStatus",
                    "jordanjcw": "jordanjcwStatus",
                    "john": "johnStatus",
                    "joe": "joeStatus",
                },
            },
            {
                "usernameToStatus": {
                    "jordanjcw": "jordanjcwStatus",
                    "joe": "joeStatus",
                    "jcw": "jcwStatus",
                },
            },
        ],
    )


def test_should_append_children_to_the_end() -> None:
    _run_sequence(
        [
            {"usernameToStatus": {"jcw": "jcwStatus", "jordanjcw": "jordanjcwStatus"}},
            {
                "usernameToStatus": {
                    "jcw": "jcwStatus",
                    "jordanjcw": "jordanjcwStatus",
                    "jordanjcwnew": "jordanjcwnewStatus",
                },
            },
        ],
    )


def test_should_append_multiple_children_to_the_end() -> None:
    _run_sequence(
        [
            {"usernameToStatus": {"jcw": "jcwStatus", "jordanjcw": "jordanjcwStatus"}},
            {
                "usernameToStatus": {
                    "jcw": "jcwStatus",
                    "jordanjcw": "jordanjcwStatus",
                    "jordanjcwnew": "jordanjcwnewStatus",
                    "jordanjcwnew2": "jordanjcwnewStatus2",
                },
            },
        ],
    )


def test_should_prepend_children_to_the_beginning() -> None:
    _run_sequence(
        [
            {"usernameToStatus": {"jcw": "jcwStatus", "jordanjcw": "jordanjcwStatus"}},
            {
                "usernameToStatus": {
                    "newUsername": "newUsernameStatus",
                    "jcw": "jcwStatus",
                    "jordanjcw": "jordanjcwStatus",
                },
            },
        ],
    )


def test_should_prepend_multiple_children_to_the_beginning() -> None:
    _run_sequence(
        [
            {"usernameToStatus": {"jcw": "jcwStatus", "jordanjcw": "jordanjcwStatus"}},
            {
                "usernameToStatus": {
                    "newNewUsername": "newNewUsernameStatus",
                    "newUsername": "newUsernameStatus",
                    "jcw": "jcwStatus",
                    "jordanjcw": "jordanjcwStatus",
                },
            },
        ],
    )


def test_should_not_prepend_an_empty_child_to_the_beginning() -> None:
    _run_sequence(
        [
            {"usernameToStatus": {"jcw": "jcwStatus", "jordanjcw": "jordanjcwStatus"}},
            {
                "usernameToStatus": {
                    "emptyUsername": None,
                    "jcw": "jcwStatus",
                    "jordanjcw": "jordanjcwStatus",
                },
            },
        ],
    )


def test_should_not_append_an_empty_child_to_the_end() -> None:
    _run_sequence(
        [
            {"usernameToStatus": {"jcw": "jcwStatus", "jordanjcw": "jordanjcwStatus"}},
            {
                "usernameToStatus": {
                    "jcw": "jcwStatus",
                    "jordanjcw": "jordanjcwStatus",
                    "emptyUsername": None,
                },
            },
        ],
    )


def test_should_not_insert_empty_children_in_the_middle() -> None:
    _run_sequence(
        [
            {"usernameToStatus": {"jcw": "jcwStatus", "jordanjcw": "jordanjcwStatus"}},
            {
                "usernameToStatus": {
                    "jcw": "jcwstatus2",
                    "skipOverMe": None,
                    "skipOverMeToo": None,
                    "definitelySkipOverMe": None,
                    "jordanjcw": "jordanjcwstatus2",
                },
            },
        ],
    )


def test_should_insert_one_new_child_in_the_middle() -> None:
    _run_sequence(
        [
            {"usernameToStatus": {"jcw": "jcwStatus", "jordanjcw": "jordanjcwStatus"}},
            {
                "usernameToStatus": {
                    "jcw": "jcwstatus2",
                    "insertThis": "insertThisStatus",
                    "jordanjcw": "jordanjcwstatus2",
                },
            },
        ],
    )


def test_should_insert_multiple_new_truthy_children_in_the_middle() -> None:
    _run_sequence(
        [
            {"usernameToStatus": {"jcw": "jcwStatus", "jordanjcw": "jordanjcwStatus"}},
            {
                "usernameToStatus": {
                    "jcw": "jcwstatus2",
                    "insertThis": "insertThisStatus",
                    "insertThisToo": "insertThisTooStatus",
                    "definitelyInsertThisToo": "definitelyInsertThisTooStatus",
                    "jordanjcw": "jordanjcwstatus2",
                },
            },
        ],
    )


def test_should_insert_non_empty_children_in_middle_where_nulls_were() -> None:
    _run_sequence(
        [
            {
                "usernameToStatus": {
                    "jcw": "jcwStatus",
                    "insertThis": None,
                    "insertThisToo": None,
                    "definitelyInsertThisToo": None,
                    "jordanjcw": "jordanjcwStatus",
                },
            },
            {
                "usernameToStatus": {
                    "jcw": "jcwstatus2",
                    "insertThis": "insertThisStatus",
                    "insertThisToo": "insertThisTooStatus",
                    "definitelyInsertThisToo": "definitelyInsertThisTooStatus",
                    "jordanjcw": "jordanjcwstatus2",
                },
            },
        ],
    )