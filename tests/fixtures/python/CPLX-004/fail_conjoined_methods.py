# Fixture for CPLX-004: ConjoinedMethods
# `connect()` must be called before `query()` -- temporal coupling on self._conn


class Database:
    def __init__(self):
        self._conn = None

    def connect(self, url):
        self._conn = _open(url)

    def query(self, sql):
        if self._conn is None:
            raise RuntimeError("call connect() first")
        return self._conn.execute(sql)


def _open(url):
    return object()
