import typing as t
from collections import defaultdict


class _IntervalBound(t.Protocol):
    """Protocol for annotating comparable types."""

    def __lt__(self, other: t.Any) -> bool:
        pass

    def __le__(self, other: t.Any) -> bool:
        pass

    def __eq__(self, other: object) -> bool:
        pass

    def __hash__(self) -> int:
        pass


_IntervalBoundT = t.TypeVar("_IntervalBoundT", bound=_IntervalBound)
_T = t.TypeVar("_T", bound=t.Hashable)
_CT = t.TypeVar("_CT", bound=_IntervalBound)


def interweave(  # noqa: C901
    events: t.Iterable[_T], key: t.Callable[[_T], tuple[_CT, _CT]]
) -> t.Iterator[set[_T]]:
    """
    Interweave an iterable of events into a chronological iterator of active combinations

    This function takes an iterable of events and yields combinations of events that are
    simultaneously active at some point in time.

    An event is considered active at time `T` if `key(event)[0] <= T <= key(event)[1]`.
    Each yielded combination is a set of events that share such a time `T`. Combinations
    are emitted in chronological order based on the start times of the events.

    If two events overlap exactly at a single point `T`, where one ends at `T` and the
    other begins at `T`, they are **not** considered overlapping. It is assumed that the
    second event ends an infinitesimal moment after `T`, making the events
    non-simultaneous. This allows conveniently representing sequential but
    non-overlapping events as distinct.

    The algorithm takes O(n) space and O(n log n) time, where n is the number of events.
    Therefore, it is not suitable for extremely large streams of events.

    Parameters
    ----------
    events:
        iterable of events to interweave
    key:
        a function that takes an event and returns the begin and end times of the event

    Yields:
    -------
    set[T]
        A tuple containing the chronologically next combination of elements from the
        iterable of events.

    Raises:
    -------
    ValueError: If for any event the end time is less than the begin time.
    """
    begin_to_elems = defaultdict(set)
    end_to_elems = defaultdict(set)
    for elem in events:
        begin, end = key(elem)
        if end <= begin:
            raise ValueError("End time must be greater than or equal to begin time.")
        begin_to_elems[begin].add(elem)
        end_to_elems[end].add(elem)

    if len(begin_to_elems) == 0:
        return
    begin_times = iter(sorted(begin_to_elems))
    end_times = sorted(end_to_elems)
    end_times_idx = 0

    first_begin = next(begin_times)
    combination: set[_T] = begin_to_elems[first_begin]

    for next_begin in begin_times:
        yield combination.copy()
        while True:
            end_time = end_times[end_times_idx]
            if next_begin < end_time:
                break
            combination.difference_update(end_to_elems[end_time])
            if len(combination) != 0:
                yield combination.copy()
            end_times_idx += 1
        combination.update(begin_to_elems[next_begin])

    for next_end_time in end_times[end_times_idx:]:
        yield combination.copy()
        combination.difference_update(end_to_elems[next_end_time])
        if len(combination) == 0:
            return
