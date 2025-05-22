from itertools import permutations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from eventweave import interweave


@st.composite
def non_overlapping_intervals[T](
    draw: st.DrawFn, values: st.SearchStrategy[T]
) -> list[tuple[int, int, T]]:
    deltas = draw(
        st.lists(st.tuples(st.integers(min_value=1), st.integers(min_value=1)))
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
def test_interweave_reproduces_chronologically_ordered_stream[T](
    stream: list[T],
) -> None:
    key = lambda x: (x[0], x[1])
    result = list(interweave(stream, key))
    expected = [{elem} for elem in sorted(stream)]  # type: ignore[type-var]
    assert result == expected


@pytest.mark.parametrize(
    "elements,expected",
    [
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
            [
                "01Element",
                "12Element",
                "23Element",
                "34Element",
                "45Element",
                "56Element",
                "67Element",
                "78Element",
                "89Element",
            ],
            [
                {"01Element"},
                {"12Element"},
                {"23Element"},
                {"34Element"},
                {"45Element"},
                {"56Element"},
                {"67Element"},
                {"78Element"},
                {"89Element"},
            ],
        ),
    ],
)
def test_interweave_works[T](elements: list[T], expected: list[set[T]]) -> None:
    key = lambda x: (x[0], x[1])

    for perm in permutations(elements):
        result = list(interweave(perm, key))
        assert result == expected
