"""Fixture for SMELL-002: closures inside distinct functions are not compared."""


def weekly_report(rows):
    def visible(row):
        if row.hidden:
            return False
        return row.amount > 0 and row.owner is not None

    return [r.week for r in rows if visible(r)]


def monthly_totals(rows, months):
    def visible(row):
        if row.hidden:
            return False
        return row.amount > 0 and row.owner is not None

    totals = dict.fromkeys(months, 0)
    for row in filter(visible, rows):
        totals[row.month] += row.amount
    return totals
