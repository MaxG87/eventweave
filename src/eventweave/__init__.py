import typing as t
from abc import abstractmethod


class _Comparable(t.Protocol):
    """Protocol for annotating comparable types."""

    @abstractmethod
    def __lt__(self: t.Self, other: t.Any) -> bool:
        pass


def interweave[T, CT: _Comparable](
    key: t.Callable[[T], tuple[CT, CT, T]], events: t.Collection[t.Iterable[T]]
) -> t.Iterator[tuple[T | None, ...]]:
    """
    Interweave multiple iterables into an iterator of combinations

    Args:
        *args: Iterables to interweave.

    Yields:
        tuple: A tuple containing the chronologically next combination of elements from
            the iterables.

    Raises:
        ValueError: If any of the iterables two elements were not chronologically
            sorted.
    """
    if not events:
        return
    streams_with_index = [iter(cur) for cur in events]
    # TODO: Handle possibly isolated events
    while True:
        try:
            next_elements = [next(stream) for stream in streams_with_index]
        except StopIteration:
            return
        unpacked = [key(cur) for cur in next_elements]
        yield tuple(cur[2] for cur in unpacked)
