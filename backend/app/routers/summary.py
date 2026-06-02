from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.summary import SummaryOut
from app.services import summary as summary_svc

router = APIRouter(prefix="/summary", tags=["summary"])


@router.get("", response_model=SummaryOut)
def get_summary(
    category: str | None = None,
    month: str | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
):
    return summary_svc.compute(db, category=category, month=month, search=search)
