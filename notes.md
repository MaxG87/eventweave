[
    [(a, b, val1), (b, c, val2), (c, None, val3)],
    [(b, d, val4), (e, None, val5)]
]
==> [[val1], [val1, val4], [val2, val4], ...]

[
    [(0, None, "First Element")],
    [(1, None, "Middle Element")],
    [(3, None, "Last Element")],
],
==> [ ("First Element"), ("First Element", "Middle Element"), ("First Element", "Middle Element", "Last Element") ]
