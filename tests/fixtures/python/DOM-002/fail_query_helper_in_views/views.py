# Fixture for DOM-002: module-level helpers in a view file query the ORM and
# decide on the result. Every function is short and no if/elif chain reaches
# four branches, yet the loan policy lives in the outer layer. The first
# helper queries through a related manager's queryset method, the second only
# through the model manager.
import functools

from django.shortcuts import render

from library.models import Loan


def _member_can_borrow(member):
    limit = member.plan.loan_limit
    if limit is None:
        return True
    active = member.loans.filter(returned_at__isnull=True).count()
    return active < limit


def _renewal_allowed(loan_id):
    loan = Loan.objects.get(pk=loan_id)
    if not loan.title.renewable:
        return False
    return loan.renewals < 2


def borrow_page(request):
    member = request.user.member
    return render(request, "borrow.html", {"can_borrow": _member_can_borrow(member)})


def overdue_fines(member):
    total = 0
    for loan in member.loans.filter(returned_at__isnull=True):
        total += loan.fine_due()
    return total


@functools.cache
def _branch_is_open(branch_id):
    if not branch_id:
        return False
    return bool(Loan.objects.values_list("branch__open", flat=True).first())


def _oldest_unreturned(member):
    loans = list(member.loans.filter(returned_at__isnull=True).order_by("due_at"))
    while loans and loans[0].waived:
        loans.pop(0)
    return loans[0] if loans else None


def _loan_state(loan_id):
    match Loan.objects.filter(pk=loan_id).values_list("state", flat=True).first():
        case "lost":
            return "billed"
        case _:
            return "open"
