# Negative fixture for CPLX-004: state set in __init__, no temporal coupling.


class WellDesigned:
    def __init__(self, conn):
        self._conn = conn

    def query(self, sql):
        return self._conn.execute(sql)
