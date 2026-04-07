"""Fixture for SA-SCALE-001: relationship() declares its loading strategy."""

from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Order(Base):
    __tablename__ = "orders"
    items = relationship("Item", lazy="selectin")
