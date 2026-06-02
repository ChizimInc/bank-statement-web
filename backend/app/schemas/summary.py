from decimal import Decimal

from pydantic import BaseModel


class CategoryBreakdown(BaseModel):
    category: str
    income: Decimal
    spending: Decimal
    balance: Decimal


class CurrencySummary(BaseModel):
    currency: str
    income: Decimal
    spending: Decimal
    balance: Decimal
    by_category: list[CategoryBreakdown]


class SummaryOut(BaseModel):
    currencies: list[CurrencySummary]
