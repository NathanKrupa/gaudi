# Negative fixture for CPLX-003: every public signature exposes only public types.


class PublicRow:
    pass


class PublicQuery:
    pass


def fetch_row(row_id: int) -> PublicRow:
    return PublicRow()


def run_query(query: PublicQuery) -> PublicRow:
    return PublicRow()


def _internal_only(row: PublicRow) -> PublicRow:
    return row
