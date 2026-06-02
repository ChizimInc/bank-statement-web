from sqlalchemy.orm import Session

from app.models.rule import CategoryRule
from app.models.transaction import Transaction


def categorize(description: str, rules: list[CategoryRule]) -> str:
    desc_lower = description.lower()
    for rule in sorted(rules, key=lambda r: (-r.priority, r.id)):
        if rule.pattern.lower() in desc_lower:
            return rule.category
    return "Uncategorized"


def categorize_all(db: Session) -> int:
    rules = db.query(CategoryRule).order_by(CategoryRule.priority.desc(), CategoryRule.id).all()
    transactions = db.query(Transaction).all()
    updated = 0
    for tx in transactions:
        new_category = categorize(tx.description, rules)
        if tx.category != new_category:
            tx.category = new_category
            updated += 1
    if updated:
        db.commit()
    return updated
