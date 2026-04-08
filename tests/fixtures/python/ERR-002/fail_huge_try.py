"""Fixture for ERR-002: try block wrapping 15 statements (well over the 10 threshold)."""


def process(payload):
    try:
        a = payload["a"]
        b = payload["b"]
        c = payload["c"]
        d = payload["d"]
        e = payload["e"]
        f = a + b
        g = c + d
        h = e + f
        i = g + h
        j = i * 2
        k = j - 1
        l = k + a
        m = l + b
        n = m + c
        o = n + d
        return o
    except KeyError:
        return None
