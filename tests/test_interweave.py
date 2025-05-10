from eventweave import interweave


def test_no_event_iters() -> None:
    key = lambda x: (x, x, x)
    result = interweave(key, [])
    assert next(result, None) is None
