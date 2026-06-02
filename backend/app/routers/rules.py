from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.rule import RuleIn, RuleOut
from app.services import rules as rules_svc
from app.services.category import categorize_all

router = APIRouter(prefix="/rules", tags=["rules"])


@router.get("", response_model=list[RuleOut])
def get_rules(db: Session = Depends(get_db)):
    return rules_svc.list_rules(db)


@router.post("", response_model=RuleOut, status_code=201)
def create_rule(data: RuleIn, db: Session = Depends(get_db)):
    return rules_svc.create_rule(db, data)


@router.post("/apply")
def apply_rules(db: Session = Depends(get_db)):
    updated = categorize_all(db)
    return {"updated": updated}


@router.put("/{rule_id}", response_model=RuleOut)
def update_rule(rule_id: int, data: RuleIn, db: Session = Depends(get_db)):
    rule = rules_svc.update_rule(db, rule_id, data)
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule


@router.delete("/{rule_id}", status_code=204)
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    if not rules_svc.delete_rule(db, rule_id):
        raise HTTPException(status_code=404, detail="Rule not found")
