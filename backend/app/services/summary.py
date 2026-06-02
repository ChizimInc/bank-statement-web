from collections import defaultdict
from decimal import Decimal

from sqlalchemy.orm import Session

from app.schemas.summary import CategoryBreakdown, CurrencySummary, SummaryOut
from app.services.transactions import list_transactions


def compute(
    db: Session,
    *,
    category: str | None = None,
    month: str | None = None,
    search: str | None = None,
) -> SummaryOut:
    transactions = list_transactions(db, category=category, month=month, search=search)

    # {currency: {category: [amounts]}}
    grouped: dict[str, dict[str, list[Decimal]]] = defaultdict(lambda: defaultdict(list))
    for tx in transactions:
        grouped[tx.currency][tx.category].append(Decimal(str(tx.amount)))

    result: list[CurrencySummary] = []
    for currency in sorted(grouped):
        by_cat = grouped[currency]

        breakdowns = [
            CategoryBreakdown(
                category=cat,
                income=sum((a for a in amounts if a > 0), Decimal(0)),
                spending=sum((a for a in amounts if a < 0), Decimal(0)),
                balance=sum(amounts, Decimal(0)),
            )
            for cat, amounts in sorted(by_cat.items())
        ]

        all_amounts = [a for amounts in by_cat.values() for a in amounts]
        result.append(CurrencySummary(
            currency=currency,
            income=sum((a for a in all_amounts if a > 0), Decimal(0)),
            spending=sum((a for a in all_amounts if a < 0), Decimal(0)),
            balance=sum(all_amounts, Decimal(0)),
            by_category=breakdowns,
        ))

    return SummaryOut(currencies=result)
