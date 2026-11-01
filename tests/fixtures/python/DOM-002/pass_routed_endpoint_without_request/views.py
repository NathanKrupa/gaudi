# Fixture for DOM-002: a routed endpoint whose framework injects dependencies
# rather than a ``request`` argument is a view, not a helper, and must NOT
# trigger even though it queries and checks the result.
from fastapi import APIRouter, Depends, HTTPException

from library.db import session
from library.models import Loan

router = APIRouter()


@router.get("/loans/{loan_id}")
def read_loan(loan_id: int, db=Depends(session)):
    loan = db.query(Loan).filter(Loan.id == loan_id).first()
    if loan is None:
        raise HTTPException(status_code=404)
    return loan
