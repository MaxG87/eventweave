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
        for bound in self.begin_times_of_atomics[self.begin_times_of_atomics_idx :]:
            yield frozenset(self.bound_to_events[bound])

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


@dataclass
class _EventWeaver[Event: t.Hashable, IntervalBound: _IntervalBound]:
    """Encapsulates the state for the interweave algorithm."""

    begin_to_elems: dict[IntervalBound, set[Event]]
    end_to_elems: dict[IntervalBound, set[Event]]
    atomic_events_interweaver: _AtomicEventInterweaver[Event, IntervalBound]
    begin_times: list[IntervalBound]
    end_times: list[IntervalBound]
    combination: frozenset[Event]
    next_begin_idx: int = 0
    end_times_idx: int = 0

    @classmethod
    def from_element_mappings(
        cls,
        begin_to_elems: dict[IntervalBound, set[Event]],
        end_to_elems: dict[IntervalBound, set[Event]],
        atomic_events_interweaver: _AtomicEventInterweaver[Event, IntervalBound],
    ) -> t.Self:
        if not _has_elements(begin_to_elems):
            raise ValueError("There must be elements to interweave!")
        begin_times = sorted(begin_to_elems)
        first_begin = begin_times[0]
        end_times = sorted(end_to_elems)

        return cls(
            atomic_events_interweaver=atomic_events_interweaver,
            begin_times=begin_times,
            begin_to_elems=begin_to_elems,
            combination=frozenset(begin_to_elems[first_begin]),
            end_times=end_times,
            end_to_elems=end_to_elems,
            next_begin_idx=0,
        )

    def yield_leading_events(self) -> t.Iterable[frozenset[Event]]:
        """Yield leading events based on the first begin time."""
        first_begin = self.begin_times[0]
        return self.atomic_events_interweaver.yield_leading_events(first_begin)

    def yield_trailing_events(self) -> t.Iterable[frozenset[Event]]:
        """Yield trailing events based on the last end time."""
        if not self.end_times:
            return []
        return self.atomic_events_interweaver.yield_remaining_events()

    def interweave_atomic_events(self) -> t.Iterable[frozenset[Event]]:
        """Interweave atomic events with the current combination."""
        next_begin = self.begin_times[self.next_begin_idx]
        yield from self.atomic_events_interweaver.interweave_atomic_events(
            self.combination, next_begin
        )
        self.next_begin_idx += 1

    def process_next_begin_time(
        self,
    ) -> t.Iterable[frozenset[Event]]:
        """Process a single begin time in the interweaving algorithm."""
        yield self.combination
        next_begin = self.begin_times[self.next_begin_idx]

        # Process end times until we reach the next begin time
        while self.end_times_idx < len(self.end_times):
            end_time = self.end_times[self.end_times_idx]

            yield from self.atomic_events_interweaver.interweave_atomic_events(
                self.combination, min(next_begin, end_time)
            )

            if next_begin < end_time:
                break

            # Remove ended events from combination
            self.combination = self.combination.difference(self.end_to_elems[end_time])

            # Yield combination if needed
            event_ends_when_next_starts = end_time in self.begin_to_elems
            if _has_elements(self.combination) and not event_ends_when_next_starts:
                yield self.combination

            self.end_times_idx += 1

        # Add new events to combination
        self.combination = self.combination.union(self.begin_to_elems[next_begin])
        self.next_begin_idx += 1

    def drop_off_events_chronologically(self) -> t.Iterable[frozenset[Event]]:
        next_end_time = self.end_times[self.end_times_idx]
        yield self.combination
        yield from self.atomic_events_interweaver.interweave_atomic_events(
            self.combination, next_end_time
        )
        self.combination = self.combination.difference(self.end_to_elems[next_end_time])
        self.end_times_idx += 1

    def has_next_begin(self) -> bool:
        """Check if there is a next begin time."""
        return self.next_begin_idx < len(self.begin_to_elems)

    def has_next_end(self) -> bool:
        """Check if there is a next begin time."""
        return self.end_times_idx < len(self.end_to_elems)


def interweave[Event: t.Hashable, IntervalBound: _IntervalBound](
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
    atomic_events_interweaver = _AtomicEventInterweaver(bound_to_events=atomic_events)

    # Handle edge case: no interval events, only atomic events
    if not _has_elements(begin_to_elems):
        yield from _handle_atomic_only_case(atomic_events_interweaver)
        return

    # Initialize state
    state = _EventWeaver.from_element_mappings(
        begin_to_elems, end_to_elems, atomic_events_interweaver
    )

    # Yield atomic events strictly before the first begin time of interval events
    yield from state.yield_leading_events()

    # Yield initial interval events with all atomic events startin at the first begin
    # time
    yield from state.interweave_atomic_events()

    # Process each subsequent begin time
    while state.has_next_begin():
        yield from state.process_next_begin_time()

    # Drop off elements in chronological order until the end times are exhausted
    while state.has_next_end():
        yield from state.drop_off_events_chronologically()

    # Yield any remaining atomic events
    yield from state.yield_trailing_events()


def _handle_atomic_only_case[Event: t.Hashable, IntervalBound: _IntervalBound](
    atomic_events_interweaver: _AtomicEventInterweaver[Event, IntervalBound],
) -> t.Iterator[frozenset[Event]]:
    """Handle the case where there are only atomic events."""
    if _has_elements(atomic_events_interweaver.bound_to_events):
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
