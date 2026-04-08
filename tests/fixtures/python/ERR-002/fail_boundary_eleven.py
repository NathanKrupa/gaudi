"""Fixture for ERR-002 boundary: 11 statements is just over the threshold."""


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
        j = i + 1
        k = j + 2
        return k
    except IndexError:
        return None
