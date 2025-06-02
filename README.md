# eventweave

**Eventweave** is a lightweight Python utility that groups overlapping events
into chronological combinations. It is useful for temporal reasoning and event
sourcing, allowing you to analyze and visualize the relationships between
events that occur simultaneously.

## Features

- Accepts any iterable of events with user-defined start and end times
- Yields sets of events that are simultaneously active at some point in time
- Handles edge cases for back-to-back, non-overlapping intervals
- Supports atomic events that start and end at the same time
- Runs in `O(n log n)` time and `O(n)` space

## Installation

This project is self-contained with no dependencies beyond the Python standard library.

You can install it using pip:

```bash
python -m pip install eventweave
```

Supported for Python 3.13 and above.

## Example Usage

Define your events and a key function:

    >>> from eventweave import interweave
    >>>
    >>> events = [
    ...     ("A", (1, 4)),
    ...     ("B", (2, 5)),
    ...     ("C", (5, 6)),
    ... ]
    >>>
    >>> def key(event):
    ...     return event[1]

Use interweave to iterate over overlapping combinations:

    >>> result = list(interweave(events, key))
    >>> expected = [
    ...     {('A', (1, 4))},
    ...     {('A', (1, 4)), ('B', (2, 5))},
    ...     {('B', (2, 5))},
    ...     {('C', (5, 6))},
    ... ]
    >>> assert result == expected

## Clarification of Overlapping Events

If one event ends at time `T` and another begins at time `T`, they are **not
considered overlapping**. The model assumes the starting event ends just after
`T` to preserve strict separation of events that merely touch.

**Instantaneous events** - where the start and end times are the same - are
considered to be active exactly at this point in time. If an event `E` starts
and ends at time `T`, it will overlap with any other event that ends at `T`.
However, it will not overlap with any event that starts at `T`, due to the
rule above.
