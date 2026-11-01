# Fixture for DOM-002: a view function (it takes the request) that queries the
# ORM and checks the result is ordinary request handling and must NOT trigger.
from django.http import Http404
from django.shortcuts import render

from library.models import Loan


def loan_detail(request, loan_id):
    loan = Loan.objects.filter(pk=loan_id, member=request.user.member).first()
    if loan is None:
        raise Http404
    return render(request, "loan.html", {"loan": loan})


def _scoped_loans(member, *, request):
    loans = Loan.objects.filter(member=member)
    if request.GET.get("open"):
        loans = loans.filter(returned_at__isnull=True)
    return loans


def loan_count(request, /):
    total = 0
    for _loan in Loan.objects.filter(member=request.user.member):
        total += 1
    return total
