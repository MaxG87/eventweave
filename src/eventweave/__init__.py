import typing as t


def interweave[T, Ord](*args: t.Iterable[T]) -> t.Iterator[tuple[T, ...]]:
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
    raise ValueError(
        "This function is not implemented yet. Please check the documentation for "
        "more information."
    )
