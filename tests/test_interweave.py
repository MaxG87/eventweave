import pytest

from eventweave import interweave


def test_no_event_iters() -> None:
    key = lambda x: (x, x, x)
    result = interweave(key, [])
    assert next(result, None) is None


@pytest.mark.parametrize(
    "elements",
    [
        [((0, 1), "A"), ((2, 3), "B")],
        [((0.0, 0.1), 1337), ((0.2, 0.3), 1312), ((0.4, 0.5), 161)],
    ],
)
def test_single_iter_is_replicated(elements) -> None:  # type: ignore[no-untyped-def]
    key = lambda x: (x[0][0], x[0][1], x[1])
    result = list(interweave(key, [elements]))
    expected = [(cur[1],) for cur in elements]
    assert result == expected
