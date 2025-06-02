import typing as t
from collections import defaultdict
from dataclasses import dataclass, field


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


@dataclass
class _AtomicEventInterweaver[Event: t.Hashable, IntervalBound: _IntervalBound]:
    begin_times_of_atomics: list[IntervalBound] = field(init=False)
    bound_to_events: dict[IntervalBound, set[Event]]
    begin_times_of_atomics_idx: int = 0

    def __post_init__(self) -> None:
        self.begin_times_of_atomics = sorted(self.bound_to_events)

    def yield_leading_events(
        self, until: IntervalBound
    ) -> t.Iterable[frozenset[Event]]:
        while True:
            try:
                start_end = self.begin_times_of_atomics[self.begin_times_of_atomics_idx]
            except IndexError:
                break
            if start_end >= until:
                break
            yield frozenset(self.bound_to_events[start_end])
            self.begin_times_of_atomics_idx += 1

    def yield_remaining_events(self) -> t.Iterable[frozenset[Event]]:
        yield from _handle_case_of_only_atomic_events(
            {
                bound: self.bound_to_events[bound]
                for bound in self.begin_times_of_atomics[
                    self.begin_times_of_atomics_idx :
                ]
            }
        )

    def interweave_atomic_events(
        self,
        active_combination: frozenset[Event],
        until: IntervalBound,
    ) -> t.Iterable[frozenset[Event]]:
        while True:
            try:
                start_end = self.begin_times_of_atomics[self.begin_times_of_atomics_idx]
            except IndexError:
                break
            if start_end > until:
                break
            yield active_combination.union(self.bound_to_events[start_end])
            if _has_elements(active_combination) and start_end != until:
                yield active_combination
            self.begin_times_of_atomics_idx += 1


def interweave[Event: t.Hashable, IntervalBound: _IntervalBound](  # noqa: C901
    events: t.Iterable[Event],
    key: t.Callable[[Event], tuple[IntervalBound, IntervalBound]],
) -> t.Iterator[frozenset[Event]]:
    """
    Interweave an iterable of events into a chronological iterator of active combinations

    This function takes an iterable of events and yields combinations of events that are
    simultaneously active at some point in time.

    An event is considered active at time `T` if `key(event)[0] <= T <= key(event)[1]`.
    Each yielded combination is a frozenset of events that share such a time `T`.
    Combinations are emitted in chronological order based on the start times of the
    events.

    If two events overlap exactly at a single point `T`, where one ends at `T` and the
    other begins at `T`, they are **not** considered overlapping. It is assumed that the
    second event ends an infinitesimal moment after `T`, making the events
    non-simultaneous. This allows conveniently representing sequential but
    non-overlapping events as distinct.

    An instantaneous event, where the begin and end times are equal, is considered
    active at that point in time. If there is a normal event that starts when some
    instantaneous event ends, the rule above applies, and the two events are
    considered non-overlapping.

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
    frozenset[T]
        A tuple containing the chronologically next combination of elements from the
        iterable of events.

    Raises:
    -------
    ValueError: If for any event the end time is less than the begin time.

    Examples
    --------
    >>> from dataclasses import dataclass
    >>> from eventweave import interweave
    >>>
    >>> @dataclass(frozen=True)
    ... class Event:
    ...         begin: str
    ...         end: str
    >>>
    >>> events = [
    ...     Event("2022-01-01", "2025-01-01"),
    ...     Event("2023-01-01", "2023-01-03"),
    ...     Event("2023-01-02", "2023-01-04"),
    ... ]
    >>> result = list(interweave(events, lambda e: (e.begin, e.end)))
    >>> expected = [
    ...     {Event("2022-01-01", "2025-01-01")},
    ...     {Event("2022-01-01", "2025-01-01"), Event("2023-01-01", "2023-01-03")},
    ...     {
    ...         Event("2022-01-01", "2025-01-01"),
    ...         Event("2023-01-01", "2023-01-03"),
    ...         Event("2023-01-02", "2023-01-04"),
    ...     },
    ...     {Event("2022-01-01", "2025-01-01"), Event("2023-01-02", "2023-01-04")},
    ...     {Event("2022-01-01", "2025-01-01")},
    ... ]
    >>> assert result == expected
    """
    begin_to_elems, end_to_elems, atomic_events = _consume_event_stream(events, key)

    if not _has_elements(begin_to_elems):
        if _has_elements(atomic_events):
            yield from _handle_case_of_only_atomic_events(atomic_events)
        return
    begin_times = iter(sorted(begin_to_elems))
    end_times = sorted(end_to_elems)
    end_times_idx = 0

    first_begin = next(begin_times)

    atomic_events_interweaver = _AtomicEventInterweaver(bound_to_events=atomic_events)
    yield from atomic_events_interweaver.yield_leading_events(first_begin)

    combination = frozenset(begin_to_elems[first_begin])
    yield from atomic_events_interweaver.interweave_atomic_events(
        combination, first_begin
    )

    for next_begin in begin_times:
        yield combination
        while True:
            end_time = end_times[end_times_idx]
            yield from atomic_events_interweaver.interweave_atomic_events(
                combination, min(next_begin, end_time)
            )
            if next_begin < end_time:
                break
            combination = combination.difference(end_to_elems[end_time])
            if _has_elements(combination) and end_time not in begin_to_elems:
                yield combination
            end_times_idx += 1
        combination = combination.union(begin_to_elems[next_begin])

    for next_end_time in end_times[end_times_idx:]:
        yield combination
        yield from atomic_events_interweaver.interweave_atomic_events(
            combination, next_end_time
        )
        combination = combination.difference(end_to_elems[next_end_time])

    yield from atomic_events_interweaver.yield_remaining_events()


def _has_elements(collection: t.Sized) -> bool:
    return len(collection) > 0


def _consume_event_stream[Event, IntervalBound: _IntervalBound](
    stream: t.Iterable[Event],
    key: t.Callable[[Event], tuple[IntervalBound, IntervalBound]],
) -> tuple[
    dict[IntervalBound, set[Event]],
    dict[IntervalBound, set[Event]],
    dict[IntervalBound, set[Event]],
]:
    begin_to_elems = defaultdict(set)
    end_to_elems = defaultdict(set)
    atomic_events = defaultdict(set)

    for elem in stream:
        begin, end = key(elem)
        if begin < end:
            begin_to_elems[begin].add(elem)
            end_to_elems[end].add(elem)
        elif begin == end:
            atomic_events[begin].add(elem)
        else:
            raise ValueError("End time must be greater than or equal to begin time.")
    return begin_to_elems, end_to_elems, atomic_events


def _handle_case_of_only_atomic_events[
    Event: t.Hashable,
    IntervalBound: _IntervalBound,
](atomic_events: dict[IntervalBound, set[Event]]) -> t.Iterable[frozenset[Event]]:
    for _, events in sorted(atomic_events.items()):
        yield frozenset(events)
