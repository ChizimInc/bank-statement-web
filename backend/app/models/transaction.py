from sqlalchemy import Column, Date, Integer, Numeric, String

from app.db import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False)
    value_date = Column(Date, nullable=True)
    description = Column(String, nullable=False)
    reference = Column(String, nullable=True)
    amount = Column(Numeric(precision=18, scale=4), nullable=False)
    currency = Column(String(10), nullable=False)
    category = Column(String, nullable=False, default="Uncategorized")
    dedup_hash = Column(String(64), unique=True, nullable=False, index=True)
