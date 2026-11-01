# Fixture for DOM-002: a class-based view's framework hook queries and branches
# as ordinary request handling; methods are not module-level helpers and must
# NOT trigger.
from django.views.generic import ListView

from library.models import Loan


class LoanList(ListView):
    def get_queryset(self):
        qs = Loan.objects.filter(member=self.request.user.member)
        if self.request.GET.get("open"):
            qs = qs.filter(returned_at__isnull=True)
        return qs
