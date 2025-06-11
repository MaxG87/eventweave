import typing as t
from collections import defaultdict
from dataclasses import dataclass, field

type KeyFuncT[Event, IntervalBound] = t.Callable[
    [Event], tuple[IntervalBound | None, IntervalBound | None]
]


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


@dataclass(frozen=True)
class _ConsumedEventStream[Event: t.Hashable, IntervalBound: _IntervalBound]:
    """A dataclass to hold the consumed event stream data."""

    elements_without_begin: set[Event]
    begin_to_elems: dict[IntervalBound, set[Event]]
    end_to_elems: dict[IntervalBound, set[Event]]
    atomic_events: dict[IntervalBound, set[Event]]

    @classmethod
    def from_stream(  # noqa: C901
        cls, stream: t.Iterable[Event], key: KeyFuncT[Event, IntervalBound]
    ) -> t.Self:
        elements_without_begin = set()
        begin_to_elems: dict[IntervalBound, set[Event]] = defaultdict(set)
        end_to_elems: dict[IntervalBound, set[Event]] = defaultdict(set)
        atomic_events: dict[IntervalBound, set[Event]] = defaultdict(set)

        # Note: mypy does not support type narrowing in tuples. Therefore it falsely reports
        # that maybe_begin and maybe_end can be None even though all cases of being None are
        # handled explicitly. In a future version of mypy it may be possible to remove the
        # `# type: ignore` comments.
        for elem in stream:
            maybe_begin, maybe_end = key(elem)
            match (maybe_begin, maybe_end):
                case (None, None):
                    elements_without_begin.add(elem)
                case (None, end):
                    elements_without_begin.add(elem)
                    end_to_elems[end].add(elem)  # type: ignore[index]
                case (begin, None):
                    begin_to_elems[begin].add(elem)  # type: ignore[index]
                case (begin, end) if begin < end:  # type: ignore[operator]
                    begin_to_elems[begin].add(elem)  # type: ignore[index]
                    end_to_elems[end].add(elem)  # type: ignore[index]
                case (begin, end) if begin == end:
                    atomic_events[begin].add(elem)  # type: ignore[index]
                case _:
                    raise ValueError(
                        "End time must be greater than or equal to begin time."
                    )
        return cls(elements_without_begin, begin_to_elems, end_to_elems, atomic_events)

    def has_interval_events(self) -> bool:
        """Check if there are any non-atomic events."""
        return (
            _has_elements(self.begin_to_elems)
            or _has_elements(self.end_to_elems)
            or _has_elements(self.elements_without_begin)
        )


@dataclass
class _AtomicEventInterweaver[Event: t.Hashable, IntervalBound: _IntervalBound]:
    begin_times_of_atomics: list[IntervalBound] = field(init=False)
    bound_to_events: dict[IntervalBound, set[Event]]
    begin_times_of_atomics_idx: int = 0

    def __post_init__(self) -> None:
        self.begin_times_of_atomics = sorted(self.bound_to_events)

    def has_remaining_events(self) -> bool:
        """Check if there are any atomic events left to yield."""
        return self.begin_times_of_atomics_idx < len(self.begin_times_of_atomics)

    def yield_leading_events(
        self, combination: frozenset[Event], until: IntervalBound | None
    ) -> t.Iterable[frozenset[Event]]:
        while True:
            try:
                start_end = self.begin_times_of_atomics[self.begin_times_of_atomics_idx]
            except IndexError:
                break
            if until is not None and start_end >= until:
                break
            yield combination.union(self.bound_to_events[start_end])
            self.begin_times_of_atomics_idx += 1

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

    def interweave_remaining_events(
        self, active_combination: frozenset[Event]
    ) -> t.Iterable[frozenset[Event]]:
        for bound in self.begin_times_of_atomics[self.begin_times_of_atomics_idx :]:
            yield active_combination.union(frozenset(self.bound_to_events[bound]))


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
        consumed_stream: _ConsumedEventStream[Event, IntervalBound],
        atomic_events_interweaver: _AtomicEventInterweaver[Event, IntervalBound],
    ) -> t.Self:
        begin_times = sorted(consumed_stream.begin_to_elems)
        end_times = sorted(consumed_stream.end_to_elems)

        return cls(
            atomic_events_interweaver=atomic_events_interweaver,
            begin_times=begin_times,
            begin_to_elems=consumed_stream.begin_to_elems,
            combination=frozenset(consumed_stream.elements_without_begin),
            end_times=end_times,
            end_to_elems=consumed_stream.end_to_elems,
            next_begin_idx=0,
        )

    def has_remaining_atomic_events(self) -> bool:
        """Check if there are any atomic events."""
        return self.atomic_events_interweaver.has_remaining_events()

    def yield_leading_atomic_events(self) -> t.Iterable[frozenset[Event]]:
        """Yield atomic events that start before the first begin time."""
        try:
            first_begin = self.begin_times[0]
        except IndexError:
            first_begin = None
        return self.atomic_events_interweaver.yield_leading_events(
            self.combination, first_begin
        )

    def activate_very_first_interval_events(self) -> None:
        if not _has_elements(self.begin_times):
            return
        first_begin = self.begin_times[0]
        self.combination = self.combination.union(self.begin_to_elems[first_begin])

    def interweave_trailing_atomic_events(self) -> t.Iterable[frozenset[Event]]:
        """Yield trailing events based on the last end time."""
        if not self.end_times:
            return
        if _has_elements(self.combination):
            yield self.combination
        if self.atomic_events_interweaver.has_remaining_events():
            yield from self.atomic_events_interweaver.interweave_remaining_events(
                self.combination
            )
            if _has_elements(self.combination):
                yield self.combination

    def interweave_atomic_events(self) -> t.Iterable[frozenset[Event]]:
        """Interweave atomic events with the current combination."""
        if not _has_elements(self.begin_times):
            return
        next_begin = self.begin_times[self.next_begin_idx]
        yield from self.atomic_events_interweaver.interweave_atomic_events(
            self.combination, next_begin
        )
        self.next_begin_idx += 1

    def interweave_events_without_begin(self) -> t.Iterable[frozenset[Event]]:
        """Interweave atomic events before any begin time."""
        maybe_next_begin = self.first_begin_time()
        if not _has_elements(self.combination):
            return
        yield self.combination
        # Process end times until we reach the next begin time
        yield from self.drop_off_events_chronologically_until(maybe_next_begin)

    def first_begin_time(self) -> IntervalBound | None:
        maybe_first_begin_interval = self.begin_times[0] if self.begin_times else None
        maybe_first_begin_atomic = (
            self.atomic_events_interweaver.begin_times_of_atomics[0]
            if self.atomic_events_interweaver.begin_times_of_atomics
            else None
        )
        match (maybe_first_begin_interval, maybe_first_begin_atomic):
            case (None, None):
                return None
            case (None, atomic_begin):
                return atomic_begin
            case (interval_begin, None):
                return interval_begin
            case (interval_begin, atomic_begin):
                return min(interval_begin, atomic_begin)  # type: ignore[type-var]
            case _:
                t.assert_never(self)  # type: ignore[arg-type]

    def process_next_begin_time(
        self,
    ) -> t.Iterable[frozenset[Event]]:
        """Process a single begin time in the interweaving algorithm."""
        yield self.combination
        next_begin = self.begin_times[self.next_begin_idx]

        # Process end times until we reach the next begin time
        yield from self.drop_off_events_chronologically_until(next_begin)

        # Add new events to combination
        self.combination = self.combination.union(self.begin_to_elems[next_begin])
        self.next_begin_idx += 1

    def drop_off_events_chronologically(self) -> t.Iterable[frozenset[Event]]:
        next_end_time = self.end_times[self.end_times_idx]
        yield from self.atomic_events_interweaver.interweave_atomic_events(
            self.combination, next_end_time
        )
        self.combination = self.combination.difference(self.end_to_elems[next_end_time])
        self.end_times_idx += 1

    def drop_off_events_chronologically_until(
        self, until: IntervalBound | None
    ) -> t.Iterable[frozenset[Event]]:
        while self.has_next_end():
            end_time = self.end_times[self.end_times_idx]
            if until is not None:
                yield from self.atomic_events_interweaver.interweave_atomic_events(
                    self.combination, min(until, end_time)
                )
            if until is not None and until < end_time:
                break

            # Remove ended events from combination
            self.combination = self.combination.difference(self.end_to_elems[end_time])

            # Yield combination if needed
            # The semantics of back-to-back events is that the later event starts an
            # infinitesimal moment after the earlier event ends. Therefore, if the
            # current event ends at the same time the next begins, there is no point in
            # between the two events are both inactive. Thus, the intermediate
            # combination must not be yielded.
            event_ends_when_next_starts = end_time in self.begin_to_elems
            if _has_elements(self.combination) and not event_ends_when_next_starts:
                yield self.combination

            self.end_times_idx += 1

    def has_next_begin(self) -> bool:
        """Check if there is a next begin time."""
        return self.next_begin_idx < len(self.begin_to_elems)

    def has_next_end(self) -> bool:
        """Check if there is a next begin time."""
        return self.end_times_idx < len(self.end_to_elems)


def interweave[Event: t.Hashable, IntervalBound: _IntervalBound](
    events: t.Iterable[Event], key: KeyFuncT[Event, IntervalBound]
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
    consumed_stream = _ConsumedEventStream.from_stream(events, key)
    atomic_events_interweaver = _AtomicEventInterweaver(
        bound_to_events=consumed_stream.atomic_events
    )

    # Initialize state
    state = _EventWeaver.from_element_mappings(
        consumed_stream, atomic_events_interweaver
    )

    yield from state.interweave_events_without_begin()

    # Yield atomic events strictly before the first begin time of interval events
    yield from state.yield_leading_atomic_events()

    # Yield initial interval events with all atomic events starting at the first begin
    # time.
    state.activate_very_first_interval_events()
    yield from state.interweave_atomic_events()

    # Process each subsequent begin time
    while state.has_next_begin():
        yield from state.process_next_begin_time()

    # Drop off elements in chronological order until the end times are exhausted
    while state.has_next_end():
        yield state.combination
        yield from state.drop_off_events_chronologically()

    # Yield any remaining atomic events
    yield from state.interweave_trailing_atomic_events()


def _has_elements(collection: t.Sized) -> bool:
    return len(collection) > 0
