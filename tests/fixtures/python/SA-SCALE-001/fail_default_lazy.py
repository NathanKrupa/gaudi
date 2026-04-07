"""Fixture for SA-SCALE-001: relationship() with no explicit lazy strategy."""

from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Order(Base):
    __tablename__ = "orders"
    items = relationship("Item")
