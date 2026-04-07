# Fixture for DOM-001 boundary: Pydantic model with exactly 5 fields, no methods.
from pydantic import BaseModel


class Order(BaseModel):
    id: int
    customer_id: int
    total_cents: int
    currency: str
    status: str
