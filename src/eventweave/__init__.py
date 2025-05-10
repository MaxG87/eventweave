import typing as t
from abc import abstractmethod


class _Comparable(t.Protocol):
    """Protocol for annotating comparable types."""

    @abstractmethod
    def __lt__(self: t.Self, other: t.Any) -> bool:
        pass


def interweave[T, CT: _Comparable](
    key: t.Callable[[T], tuple[CT, CT, T]], events: t.Collection[t.Iterable[T]]
) -> t.Iterator[tuple[T, ...]]:
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
    raise ValueError(
        "This function is not implemented yet. Please check the documentation for "
        "more information."
    )
    yield  # type: ignore[unreachable]
