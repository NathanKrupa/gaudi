# Fixture for CPLX-003: InformationLeakage
# Public functions whose signatures expose private types


class _InternalRow:
    pass


class PublicRow:
    pass


def fetch_row(row_id: int) -> _InternalRow:  # leakage in return
    return _InternalRow()


def store_row(row: _InternalRow) -> None:  # leakage in parameter
    pass


def safe_fetch(row_id: int) -> PublicRow:  # OK -- public type
    return PublicRow()


def _internal_helper(row: _InternalRow) -> _InternalRow:  # private function -- not flagged
    return row
