from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.rule import CategoryRule
from app.models.transaction import Transaction
from app.schemas.transaction import ImportResult, SkippedRow, TransactionOut
from app.services.category import categorize
from app.services.parse import ParseService

_parser = ParseService()


def run_import(file_bytes: bytes, db: Session) -> ImportResult:
    parsed = _parser.parse(file_bytes)
    rules = db.query(CategoryRule).order_by(CategoryRule.priority.desc(), CategoryRule.id).all()

    extra_skipped: list[SkippedRow] = []
    to_insert: list[Transaction] = []

    for row in parsed.rows:
        already_exists = db.execute(
            select(Transaction.id).where(Transaction.dedup_hash == row.dedup_hash)
        ).first() is not None

        if already_exists:
            extra_skipped.append(SkippedRow(
                source_line=row.source_line,
                statement_nr=row.statement_nr,
                reason="Duplicate transaction",
            ))
            continue

        to_insert.append(Transaction(
            date=row.date,
            value_date=row.value_date,
            description=row.description,
            reference=row.reference,
            amount=row.amount,
            currency=row.currency,
            category=categorize(row.description, rules),
            dedup_hash=row.dedup_hash,
        ))

    if to_insert:
        db.add_all(to_insert)
        db.commit()
        for t in to_insert:
            db.refresh(t)

    all_skipped = parsed.skipped_rows + extra_skipped

    return ImportResult(
        imported=len(to_insert),
        skipped=len(all_skipped),
        ignored=len(parsed.ignored_rows),
        skipped_rows=all_skipped,
        ignored_rows=parsed.ignored_rows,
        transactions=[TransactionOut.model_validate(t) for t in to_insert],
    )
