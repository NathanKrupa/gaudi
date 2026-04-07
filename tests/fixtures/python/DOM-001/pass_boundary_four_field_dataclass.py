# Fixture for DOM-001 boundary: Pydantic model with 4 fields is below threshold.
from pydantic import BaseModel


class Point(BaseModel):
    x: int
    y: int
    z: int
    label: str
