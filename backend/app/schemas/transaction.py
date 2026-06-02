from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, model_validator


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: date
    value_date: Optional[date]
    description: str
    reference: Optional[str]
    amount: Decimal
    currency: str
    category: str
    dedup_hash: str


class SkippedRow(BaseModel):
    source_line: int
    statement_nr: Optional[str]
    reason: str


class IgnoredRow(BaseModel):
    source_line: int
    statement_nr: Optional[str]
    reason: str


class TransactionPatch(BaseModel):
    category: str
    save_as_rule: bool = False
    pattern: Optional[str] = None

    @model_validator(mode="after")
    def pattern_required_when_save_as_rule(self) -> "TransactionPatch":
        if self.save_as_rule and not self.pattern:
            raise ValueError("pattern is required when save_as_rule is True")
        return self


class ImportResult(BaseModel):
    imported: int
    skipped: int
    ignored: int
    skipped_rows: list[SkippedRow]
    ignored_rows: list[IgnoredRow]
    transactions: list[TransactionOut]
