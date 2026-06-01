import csv
import hashlib
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

from app.schemas.transaction import IgnoredRow, SkippedRow

BALANCE_KEYWORDS = ("SOLD INITIAL", "SOLD FINAL")
HEADER_MARKER = "Descriere"


@dataclass
class ParsedRow:
    date: date
    value_date: Optional[date]
    description: str
    reference: Optional[str]
    amount: Decimal
    currency: str
    dedup_hash: str
    statement_nr: Optional[str] = None


@dataclass
class ParseResult:
    rows: list[ParsedRow] = field(default_factory=list)
    skipped_rows: list[SkippedRow] = field(default_factory=list)
    ignored_rows: list[IgnoredRow] = field(default_factory=list)


def _normalize_number(s: str) -> str:
    return s.replace(" ", "").replace(",", ".")


class ParseService:
    def parse(self, file_bytes: bytes) -> ParseResult:
        text = file_bytes.decode("utf-8-sig")
        lines = text.splitlines()

        header_line_idx = next(
            (i for i, line in enumerate(lines) if HEADER_MARKER in line), None
        )
        if header_line_idx is None:
            return ParseResult()

        result = ParseResult()
        seen_hashes: set[str] = set()
        reader = csv.DictReader(lines[header_line_idx:])

        for row_idx, row in enumerate(reader):
            # source_line is 1-based physical CSV line number
            source_line = header_line_idx + 2 + row_idx

            nr = (row.get("Nr") or "").strip()
            statement_nr = nr or None

            description = (row.get("Descriere") or "").strip()
            reference = (row.get("Referinta") or "").strip() or None
            debit_raw = (row.get("Debit") or "").strip()
            credit_raw = (row.get("Credit") or "").strip()
            currency = (row.get("Valuta") or "").strip()
            date_raw = (row.get("Data") or "").strip()
            value_date_raw = (row.get("Data valuta") or "").strip()

            if any(kw in description.upper() for kw in BALANCE_KEYWORDS):
                result.ignored_rows.append(IgnoredRow(
                    source_line=source_line,
                    statement_nr=statement_nr,
                    reason="Balance summary row",
                ))
                continue

            if not description and not debit_raw and not credit_raw:
                result.skipped_rows.append(SkippedRow(
                    source_line=source_line,
                    statement_nr=statement_nr,
                    reason="Missing description and amount",
                ))
                continue

            reasons: list[str] = []

            parsed_date: Optional[date] = None
            if date_raw:
                try:
                    parsed_date = datetime.strptime(date_raw, "%d.%m.%Y").date()
                except ValueError:
                    reasons.append("Invalid date")
            else:
                reasons.append("Invalid date")

            parsed_value_date: Optional[date] = None
            if value_date_raw:
                try:
                    parsed_value_date = datetime.strptime(value_date_raw, "%d.%m.%Y").date()
                except ValueError:
                    pass

            amount: Optional[Decimal] = None
            if debit_raw or credit_raw:
                try:
                    if debit_raw:
                        amount = -Decimal(_normalize_number(debit_raw))
                    else:
                        amount = Decimal(_normalize_number(credit_raw))
                except InvalidOperation:
                    reasons.append("Missing or invalid amount")
            else:
                reasons.append("Missing or invalid amount")

            if reasons:
                result.skipped_rows.append(SkippedRow(
                    source_line=source_line,
                    statement_nr=statement_nr,
                    reason=" and ".join(reasons),
                ))
                continue

            hash_input = (
                f"{parsed_date}|{parsed_value_date}|{description}"
                f"|{reference or ''}|{amount}|{currency}"
            )
            dedup_hash = hashlib.sha256(hash_input.encode()).hexdigest()

            if dedup_hash in seen_hashes:
                result.skipped_rows.append(SkippedRow(
                    source_line=source_line,
                    statement_nr=statement_nr,
                    reason="Duplicate transaction",
                ))
                continue

            seen_hashes.add(dedup_hash)
            result.rows.append(ParsedRow(
                date=parsed_date,
                value_date=parsed_value_date,
                description=description,
                reference=reference,
                amount=amount,
                currency=currency,
                dedup_hash=dedup_hash,
                statement_nr=statement_nr,
            ))

        return result
