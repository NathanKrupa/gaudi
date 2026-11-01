"""Fixture for SMELL-026: a docstring that narrates history."""


def due_date(loan):
    """Return when the loan is due.

    This was refactored to read the policy table.
    The due date used to be fixed at fourteen days.
    """
    return loan.start + loan.policy.period
