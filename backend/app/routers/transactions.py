from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.transaction import TransactionOut, TransactionPatch
from app.services import transactions as tx_svc

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=list[TransactionOut])
def get_transactions(
    category: str | None = None,
    month: str | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
):
    return tx_svc.list_transactions(db, category=category, month=month, search=search)


@router.patch("/{tx_id}", response_model=TransactionOut)
def patch_transaction(tx_id: int, data: TransactionPatch, db: Session = Depends(get_db)):
    tx = tx_svc.patch_transaction(db, tx_id, data)
    if tx is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return tx
