from sqlalchemy.orm import Session

from app.models.rule import CategoryRule
from app.schemas.rule import RuleIn


def list_rules(db: Session) -> list[CategoryRule]:
    return db.query(CategoryRule).order_by(CategoryRule.priority.desc(), CategoryRule.id).all()


def create_rule(db: Session, data: RuleIn) -> CategoryRule:
    rule = CategoryRule(**data.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def update_rule(db: Session, rule_id: int, data: RuleIn) -> CategoryRule | None:
    rule = db.get(CategoryRule, rule_id)
    if rule is None:
        return None
    for field, value in data.model_dump().items():
        setattr(rule, field, value)
    db.commit()
    db.refresh(rule)
    return rule


def delete_rule(db: Session, rule_id: int) -> bool:
    rule = db.get(CategoryRule, rule_id)
    if rule is None:
        return False
    db.delete(rule)
    db.commit()
    return True
