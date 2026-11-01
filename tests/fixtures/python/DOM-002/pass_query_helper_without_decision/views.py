# Fixture for DOM-002: a view-file helper that only composes a query, with no
# decision of its own, one whose only decision is a conditional expression,
# and a helper that decides without touching the ORM (presentation), must NOT
# trigger.
from django.shortcuts import render

from library.models import Loan


def _open_loans(member):
    return Loan.objects.filter(member=member, returned_at__isnull=True).order_by("due_at")


def _borrower_name(loan_id):
    loan = Loan.objects.get(pk=loan_id)
    return loan.member.name if loan.member else ""


def _due_label(loan):
    if loan.is_overdue:
        return "Overdue"
    return "Due " + loan.due_at.isoformat()


def loans_page(request):
    loans = _open_loans(request.user.member)
    return render(request, "loans.html", {"labels": [_due_label(x) for x in loans]})
