"""Fixture for ERR-002 boundary: exactly 10 statements should NOT trigger (threshold is >10)."""


def run(data):
    try:
        a = data[0]
        b = data[1]
        c = data[2]
        d = data[3]
        e = data[4]
        f = a + b
        g = c + d
        h = e + f
        i = g + h
        return i
    except IndexError:
        return None
