"""Fixture for SMELL-026: a backslash continuation must not shift line numbers."""


def due_date(loan):
    """Return when the loan is due, counted from the \
    loan start.

    It used to be fixed at fourteen days.
    """
    return loan.start + loan.policy.period
