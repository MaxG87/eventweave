import abc
import enum
import typing as t
from collections import defaultdict
from dataclasses import dataclass, field

from more_itertools import peekable

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


class EventType(enum.Enum):
    BEGIN = enum.auto()
    END = enum.auto()
    ATOMIC = enum.auto()


@dataclass(frozen=True)
class TimelineEvent[Event: t.Hashable, IntervalBound: _IntervalBound]:
    begin: IntervalBound
    event_type: EventType
    elements: set[Event]

    def add_event(self, event: Event) -> None:
        self.elements.add(event)


@dataclass(frozen=True)
class StateMachine[Event: t.Hashable, IntervalBound: _IntervalBound]:
    timeline_events: list[TimelineEvent]
    elements_without_begin: set[Event]
    current_state: State = field(default_factory=InitialState)
    active_elements: set[Event] = field(default_factory=set)

    #     @classmethod
    #     def from_events(
    #         events: t.Iterable[Event], key: KeyFuncT[Event, IntervalBound]
    #     ) -> t.Self:
    #         elements_without_begin = set()
    #         begin_events: dict[IntervalBound, TimelineEvent[Event, IntervalBound]] = {}
    #         end_events: dict[IntervalBound, TimelineEvent[Event, IntervalBound]] = {}
    #         for cur in events:
    #             maybe_begin, maybe_end = key(cur)
    #             if maybe_begin is not None and maybe_begin not in begin_events:
    #                 begin_events[maybe_begin] = TimelineEvent(
    #             match (begin, end):
    #                 case (None, None):
    #                     elements_without_begin.add(cur)
    #                 case (None, end):

    def add_elements_without_begin(self, elements: set):
        """Fügt Events ohne Begin-Zeit hinzu"""
        self.elements_without_begin.update(elements)
        self.active_elements.update(elements)

    def transition_to(self, new_state: State):
        """Wechselt zu einem neuen Zustand"""
        self.current_state = new_state

    def has_more_intervals(self) -> bool:
        """Prüft, ob noch Intervall-Events folgen"""
        return any(
            event.event_type in [EventType.BEGIN, EventType.END]
            for event in self.timeline_events
        )

    def process_events(self) -> t.Iterator[frozenset]:
        """Verarbeitet alle Events chronologisch"""
        # Initiale Ausgabe für Events ohne Begin
        if self.active_elements:
            yield frozenset(self.active_elements)

        # Timeline-Events chronologisch verarbeiten
        for event in sorted(self.timeline_events):
            if self.current_state.can_transition_to(event):
                yield from self.current_state.handle_event(self, event)


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

    If the begin time of an event is `None`, it is considered to be active before any
    other event. If the end time is `None`, the event is considered to be active until
    the end of time. If both begin and end times are `None`, the event is considered to
    be active at all times.

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
    ...     Event(None, None),
    ...     Event("2022-01-01", "2025-01-01"),
    ...     Event("2023-01-01", "2023-01-03"),
    ...     Event("2023-01-02", "2023-01-04"),
    ... ]
    >>> result = list(interweave(events, lambda e: (e.begin, e.end)))
    >>> expected = [
    ...     {Event(None, None)},
    ...     {Event(None, None), Event("2022-01-01", "2025-01-01")},
    ...     {Event(None, None), Event("2022-01-01", "2025-01-01"), Event("2023-01-01", "2023-01-03")},
    ...     {
    ...         Event(None, None),
    ...         Event("2022-01-01", "2025-01-01"),
    ...         Event("2023-01-01", "2023-01-03"),
    ...         Event("2023-01-02", "2023-01-04"),
    ...     },
    ...     {Event(None, None), Event("2022-01-01", "2025-01-01"), Event("2023-01-02", "2023-01-04")},
    ...     {Event(None, None), Event("2022-01-01", "2025-01-01")},
    ...     {Event(None, None)},
    ... ]
    >>> assert result == expected
    """

    # Zustandsautomat initialisieren
    fsm = StateMachine.from_events(events, key)
    yield from fsm.process_events()


def create_timeline_events[Event: t.Hashable, IntervalBound: _IntervalBound](
    events: t.Iterable[Event], key: KeyFuncT[Event, IntervalBound]
) -> list[TimelineEvent[Event, IntervalBound]]:
    time_type_to_elements: dict[tuple[IntervalBound, EventType], set[Event]] = (
        defaultdict(set)
    )
    elements_without_begin = set()

    for event in events:
        begin, end = key(event)

        if begin is None and end is None:
            elements_without_begin.add(event)
        elif begin is None:
            elements_without_begin.add(event)
            time_type_to_elements[(end, EventType.END)].add(event)
        elif end is None:
            time_type_to_elements[(begin, EventType.BEGIN)].add(event)
        elif begin == end:
            time_type_to_elements[(begin, EventType.ATOMIC)].add(event)
        elif begin < end:
            time_type_to_elements[(begin, EventType.BEGIN)].add(event)
            time_type_to_elements[(end, EventType.END)].add(event)
        else:
            raise ValueError("End time must be >= begin time")

    # Erstelle aggregierte TimelineEvents
    timeline_events: list[TimelineEvent[Event, IntervalBound]] = []
    for (time, event_type), element_set in time_type_to_elements.items():
        timeline_events.append(TimelineEvent(time, event_type, frozenset(element_set)))
    timeline_events.sort()
    return timeline_events


def _has_elements(collection: t.Sized) -> bool:
    return len(collection) > 0
