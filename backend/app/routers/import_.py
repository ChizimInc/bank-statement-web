from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.transaction import ImportResult
from app.services.import_ import run_import

router = APIRouter()


@router.post("/import", response_model=ImportResult)
async def import_csv(file: UploadFile, db: Session = Depends(get_db)):
    contents = await file.read()
    return run_import(contents, db)
