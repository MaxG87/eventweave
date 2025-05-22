import typing as t
from abc import abstractmethod


class _Comparable(t.Protocol):
    """Protocol for annotating comparable types."""

    @abstractmethod
    def __lt__(self: t.Self, other: t.Any) -> bool:
        pass


def interweave[T, CT: _Comparable | t.Hashable](
    events: t.Iterable[T], key: t.Callable[[T], tuple[CT, CT]]
) -> t.Iterator[set[T]]:
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
    stream = iter(events)
    while True:
        try:
            next_elem = next(stream)
        except StopIteration:
            return
        yield {next_elem}
