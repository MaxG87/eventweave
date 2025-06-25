import math
import typing as t
from itertools import permutations

import pytest
from hypothesis import example, given
from hypothesis import strategies as st

from eventweave import interweave

_E = math.exp(1)
_PI = math.pi
_PHI = (math.sqrt(5) + 1) / 2


def _make_event[Value: t.Hashable](
    tup: tuple[int | None, int | None, Value],
) -> tuple[int | None, int | None, Value]:
    match tup:
        case (None, None, value):
            return (None, None, value)
        case (begin, None, value):
            return (begin, None, value)
        case (None, end, value):
            return (None, end, value)
        case (bound1, bound2, value):
            return (min(bound1, bound2), max(bound1, bound2), value)
        case _:
            t.assert_never(tup)  # type: ignore[arg-type]


@st.composite
def non_overlapping_intervals[T](
    draw: st.DrawFn, values: st.SearchStrategy[T]
) -> list[tuple[int, int, T]]:
    deltas = draw(
        st.lists(st.tuples(st.integers(min_value=1), st.integers(min_value=0)))
    )
    intervals = []
    cur_end = 0
    for begin_delta, end_delta in deltas:
        next_value = draw(values)
        next_begin = cur_end + begin_delta
        next_end = next_begin + end_delta
        intervals.append((next_begin, next_end, next_value))
        cur_end = next_end
    permutation = draw(st.permutations(intervals))
    return permutation


def test_no_event_iters() -> None:
    key = lambda x: (x, x)
    result = interweave([], key)
    assert next(result, None) is None


@given(
    stream=non_overlapping_intervals(st.integers()),
)
@example(stream=[(1, 2, 1), (3, 4, 2), (5, 6, 3)])
def test_interweave_reproduces_chronologically_ordered_stream(
    stream: list[tuple[int | None, int | None, float]],
) -> None:
    key = lambda x: (x[0], x[1])
    result = list(interweave(stream, key))
    expected = [{elem} for elem in sorted(stream)]
    assert result == expected


@given(
    stream=st.lists(
        st.tuples(
            st.integers() | st.none(), st.integers() | st.none(), st.floats()
        ).map(_make_event),
    )
)
def test_interweave_yields_all_events_eventually[T](
    stream: list[T],
) -> None:
    key = lambda x: (x[0], x[1])
    all_events = set(stream)
    result_events: set[T] = set()
    for result in interweave(stream, key):
        result_events.update(result)
    assert result_events == all_events


@pytest.mark.parametrize(
    "elements,expected",
    [
        ([(1, 1, 0)], [{(1, 1, 0)}]),
        (
            [("a", "c", "First Element"), ("d", "f", "Last Element")],
            [{("a", "c", "First Element")}, {("d", "f", "Last Element")}],
        ),
        (
            [
                ("a", "c", "First Element"),
                ("b", "e", "Middle Element"),
                ("d", "f", "Last Element"),
            ],
            [
                {("a", "c", "First Element")},
                {("a", "c", "First Element"), ("b", "e", "Middle Element")},
                {("b", "e", "Middle Element")},
                {("b", "e", "Middle Element"), ("d", "f", "Last Element")},
                {("d", "f", "Last Element")},
            ],
        ),
        (
            ["01Element", "12Element", "23Element", "34Element", "45Element"],
            [{"01Element"}, {"12Element"}, {"23Element"}, {"34Element"}, {"45Element"}],
        ),
        (
            [
                (1, 1000, "1-1000"),
                (5, 10, "5-10"),
                (6, 7, "6-7"),
                (9, 20, "9-20"),
            ],
            [
                {(1, 1000, "1-1000")},
                {(1, 1000, "1-1000"), (5, 10, "5-10")},
                {(1, 1000, "1-1000"), (5, 10, "5-10"), (6, 7, "6-7")},
                {(1, 1000, "1-1000"), (5, 10, "5-10")},
                {(1, 1000, "1-1000"), (5, 10, "5-10"), (9, 20, "9-20")},
                {(1, 1000, "1-1000"), (9, 20, "9-20")},
                {(1, 1000, "1-1000")},
            ],
        ),
        (
            [
                (1, 6, "Long Running Event"),
                (2, 3, "Early Short Event"),
                (3, 4, "Middle Short Event"),
                (4, 5, "Late Short Event"),
            ],
            [
                {(1, 6, "Long Running Event")},  # for T in [1, 2]
                {  # for T in ]2, 3]
                    (1, 6, "Long Running Event"),
                    (2, 3, "Early Short Event"),
                },
                {  # for T in ]3, 4]
                    (1, 6, "Long Running Event"),
                    (3, 4, "Middle Short Event"),
                },
                {  # for T in ]4, 5]
                    (1, 6, "Long Running Event"),
                    (4, 5, "Late Short Event"),
                },
                {(1, 6, "Long Running Event")},  # for T in ]5, 6]
            ],
        ),
        (
            [(1, 1, 0.0), (2, 2, 0.0)],
            [{(1, 1, 0.0)}, {(2, 2, 0.0)}],
        ),
        (
            [(1, 1, 0.0), (2, 3, 0.0)],
            [{(1, 1, 0.0)}, {(2, 3, 0.0)}],
        ),
        ([(1, 2, 0), (3, 3, 0)], [{(1, 2, 0)}, {(3, 3, 0)}]),
        (
            [(0, 3, _PI), (1, 1, _PI), (2, 2, _PI)],
            [
                {(0, 3, _PI)},
                {(0, 3, _PI), (1, 1, _PI)},
                {(0, 3, _PI)},
                {(0, 3, _PI), (2, 2, _PI)},
                {(0, 3, _PI)},
            ],
        ),
        ([(1, 2, 0), (3, 3, 0), (4, 5, 0)], [{(1, 2, 0)}, {(3, 3, 0)}, {(4, 5, 0)}]),
        (
            [(1, 3, _E), (3, 3, _E), (3, 5, _E)],
            [{(1, 3, _E)}, {(1, 3, _E), (3, 3, _E)}, {(3, 5, _E)}],
        ),
        (
            [
                (1, 3, _PHI),
                (3, 3, _PHI),
                (3, 3, _E),
                (3, 3, 1337),
                (3, 5, _PHI),
                (5, 5, _PHI),
                (5, 5, 1337),
            ],
            [
                {(1, 3, _PHI)},
                {(1, 3, _PHI), (3, 3, _PHI), (3, 3, _E), (3, 3, 1337)},
                {(3, 5, _PHI)},
                {(3, 5, _PHI), (5, 5, _PHI), (5, 5, 1337)},
            ],
        ),
        (
            [(1, 1, _PI), (1, 3, _PHI), (3, 3, 1337), (3, 5, _PHI), (5, 5, 1337)],
            [
                {(1, 1, _PI), (1, 3, _PHI)},
                {(1, 3, _PHI)},
                {(1, 3, _PHI), (3, 3, 1337)},
                {(3, 5, _PHI)},
                {(3, 5, _PHI), (5, 5, 1337)},
            ],
        ),
        (
            [
                (None, 1, "None - 1"),
                (None, 2, "None - 2"),
                (2, 2, "2 - 2"),
                (2, 4, "2 - 4"),
                (3, 5, "3 - 5"),
            ],
            [
                {(None, 1, "None - 1"), (None, 2, "None - 2")},
                {(None, 2, "None - 2")},
                {(None, 2, "None - 2"), (2, 2, "2 - 2")},
                {(2, 4, "2 - 4")},
                {(2, 4, "2 - 4"), (3, 5, "3 - 5")},
                {(3, 5, "3 - 5")},
            ],
        ),
        ([(None, None, "only None")], [{(None, None, "only None")}]),
        (
            [
                (1, None, "1 - None"),
                (2, None, "2 - None"),
                (3, 5, "3 - 5"),
                (6, 6, "6 - 6"),
            ],
            [
                {(1, None, "1 - None")},
                {(1, None, "1 - None"), (2, None, "2 - None")},
                {(1, None, "1 - None"), (2, None, "2 - None"), (3, 5, "3 - 5")},
                {(1, None, "1 - None"), (2, None, "2 - None")},
                {(1, None, "1 - None"), (2, None, "2 - None"), (6, 6, "6 - 6")},
                {(1, None, "1 - None"), (2, None, "2 - None")},
            ],
        ),
        (
            [
                (None, None, "None - None"),
                (None, None, "None - None II"),
                (None, 1, "None - 1"),
                (None, 2, "None - 2"),
                (1, None, "1 - None"),
                (2, None, "2 - None"),
            ],
            [
                {  # for T in [None, 1]
                    (None, None, "None - None"),
                    (None, None, "None - None II"),
                    (None, 1, "None - 1"),
                    (None, 2, "None - 2"),
                },
                {  # for T in ]1, 2]
                    (None, None, "None - None"),
                    (None, None, "None - None II"),
                    (None, 2, "None - 2"),
                    (1, None, "1 - None"),
                },
                {  # for T in ]2, None]
                    (None, None, "None - None"),
                    (None, None, "None - None II"),
                    (1, None, "1 - None"),
                    (2, None, "2 - None"),
                },
            ],
        ),
    ],
)
def test_interweave_works[T](elements: list[T], expected: list[set[T]]) -> None:
    key = lambda x: (x[0], x[1])

    for perm in permutations(elements):
        result = list(interweave(perm, key))
        assert result == expected


@given(
    valid_stream=st.lists(
        st.tuples(st.integers(), st.integers(), st.floats()).map(
            lambda x: (min(x[0], x[1]), max(x[0], x[1]), x[2])
        ),
    ),
    invalid_element=st.tuples(st.integers(), st.integers(), st.floats())
    .filter(lambda x: x[0] != x[1])
    .map(lambda x: (max(x[0], x[1]), min(x[0], x[1]), x[2])),
)
def test_interweave_raises_value_error[T](
    valid_stream: list[T], invalid_element: T
) -> None:
    key = lambda x: (x[0], x[1])
    # list.set is a poor mans shuffle
    new_stream = list({*valid_stream, invalid_element})
    with pytest.raises(ValueError):
        list(interweave(new_stream, key))
