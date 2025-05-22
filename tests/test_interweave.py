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
    return intervals


def test_no_event_iters() -> None:
    key = lambda x: (x, x)
    result = interweave([], key)
    assert next(result, None) is None


@given(
    stream=non_overlapping_intervals(st.integers()),
)
def test_interweave_reproduces_chronologically_ordered_stream(stream) -> None:  # type: ignore[no-untyped-def]
    key = lambda x: (x[0], x[1])
    result = list(interweave(stream, key))
    expected = [{elem} for elem in stream]
    assert result == expected
