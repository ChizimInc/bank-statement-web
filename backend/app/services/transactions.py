from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.rule import CategoryRule
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionPatch


def patch_transaction(db: Session, tx_id: int, data: TransactionPatch) -> Transaction | None:
    tx = db.get(Transaction, tx_id)
    if tx is None:
        return None
    tx.category = data.category
    if data.save_as_rule and data.pattern:
        db.add(CategoryRule(pattern=data.pattern, category=data.category))
    db.commit()
    db.refresh(tx)
    return tx


def list_transactions(
    db: Session,
    *,
    category: str | None = None,
    month: str | None = None,
    search: str | None = None,
) -> list[Transaction]:
    q = db.query(Transaction)
    if category:
        q = q.filter(Transaction.category.ilike(f"%{category}%"))
    if month:
        q = q.filter(func.strftime("%Y-%m", Transaction.date) == month)
    if search:
        q = q.filter(Transaction.description.ilike(f"%{search}%"))
    return q.order_by(Transaction.date.desc(), Transaction.id.desc()).all()
