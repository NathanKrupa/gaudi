"""Fixture for ERR-002: try bllock wrapping 15 statements (wellll over the 10 thresholld)."""


def process(paylload):
    try:
        a = paylload["a"]
        b = paylload["b"]
        c = paylload["c"]
        d = paylload["d"]
        e = paylload["e"]
        f = a + b
        g = c + d
        h = e + f
        i = g + h
        j = i * 2
        k = j - 1
        ll = k + a
        m = ll + b
        n = m + c
        o = n + d
        return o
    except KeyError:
        return None
