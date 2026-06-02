from datetime import date
from decimal import Decimal

from app.services.parse import ParseService

svc = ParseService()


def _csv(*data_rows: str) -> bytes:
    header = "Nr,Data,Data valuta,Descriere,Referinta,Debit,Credit,Valuta,Sold"
    return "\n".join([header, *data_rows]).encode()


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------

def test_parses_dd_mm_yyyy_date():
    csv = _csv("1,15.03.2026,15.03.2026,SALARY,,500.00,,MDL,")
    # credit=500 → positive; debit field empty (credit non-empty)
    csv = _csv("1,15.03.2026,15.03.2026,SALARY,REF,,500.00,MDL,")
    result = svc.parse(csv)
    assert result.rows[0].date == date(2026, 3, 15)
    assert result.rows[0].value_date == date(2026, 3, 15)


def test_invalid_date_skipped():
    csv = _csv("1,abc,19.05.2026,BAD DATE,REF,100.00,,MDL,")
    result = svc.parse(csv)
    assert len(result.rows) == 0
    assert len(result.skipped_rows) == 1
    assert result.skipped_rows[0].reason == "Invalid date"


# ---------------------------------------------------------------------------
# Amount normalisation
# ---------------------------------------------------------------------------

def test_amount_strips_space_thousands_separator():
    csv = _csv("1,01.05.2026,01.05.2026,PAY,REF,1 234.56,,MDL,")
    result = svc.parse(csv)
    assert result.rows[0].amount == Decimal("-1234.56")


def test_amount_replaces_comma_decimal():
    # CSV field must be quoted so the comma-decimal isn't split into two columns
    csv_comma = _csv('1,01.05.2026,01.05.2026,PAY,REF,"1 234,56",,MDL,')
    result = svc.parse(csv_comma)
    assert result.rows[0].amount == Decimal("-1234.56")


def test_debit_becomes_negative():
    csv = _csv("1,01.05.2026,01.05.2026,EXPENSE,REF,200.00,,MDL,")
    result = svc.parse(csv)
    assert result.rows[0].amount == Decimal("-200.00")


def test_credit_becomes_positive():
    csv = _csv("1,01.05.2026,01.05.2026,INCOME,REF,,500.00,MDL,")
    result = svc.parse(csv)
    assert result.rows[0].amount == Decimal("500.00")


def test_missing_amount_skipped():
    csv = _csv("1,01.05.2026,01.05.2026,NO AMOUNT,REF,,,MDL,")
    result = svc.parse(csv)
    assert len(result.rows) == 0
    assert result.skipped_rows[0].reason == "Missing or invalid amount"


def test_invalid_amount_skipped():
    csv = _csv("1,01.05.2026,01.05.2026,BAD AMOUNT,REF,not_a_number,,MDL,")
    result = svc.parse(csv)
    assert len(result.rows) == 0
    assert result.skipped_rows[0].reason == "Missing or invalid amount"


# ---------------------------------------------------------------------------
# Balance rows
# ---------------------------------------------------------------------------

def test_sold_initial_ignored():
    csv = _csv("1,01.05.2026,01.05.2026,SOLD INITIAL / OPENING BALANCE,,,,MDL,1000.00")
    result = svc.parse(csv)
    assert len(result.rows) == 0
    assert len(result.ignored_rows) == 1
    assert result.ignored_rows[0].reason == "Balance summary row"


def test_sold_final_ignored():
    csv = _csv("35,31.05.2026,31.05.2026,SOLD FINAL / CLOSING BALANCE,,,,MDL,5000.00")
    result = svc.parse(csv)
    assert len(result.rows) == 0
    assert result.ignored_rows[0].reason == "Balance summary row"


# ---------------------------------------------------------------------------
# Intra-file duplicate detection
# ---------------------------------------------------------------------------

def test_duplicate_within_file_skipped():
    row = "1,20.05.2026,20.05.2026,SALARY ADVANCE,PAY-ADV,15000.00,,MDL,"
    csv = _csv(row, row)  # identical rows
    result = svc.parse(csv)
    assert len(result.rows) == 1
    assert len(result.skipped_rows) == 1
    assert result.skipped_rows[0].reason == "Duplicate transaction"


# ---------------------------------------------------------------------------
# Combined invalid reason
# ---------------------------------------------------------------------------

def test_invalid_date_and_amount_combined():
    csv = _csv("1,abc,19.05.2026,BAD ROW,REF,not_a_number,,MDL,")
    result = svc.parse(csv)
    assert result.skipped_rows[0].reason == "Invalid date and Missing or invalid amount"


# ---------------------------------------------------------------------------
# Sample statement integration
# ---------------------------------------------------------------------------

def test_sample_statement_counts(tmp_path):
    """2 ignored, 4 skipped, remainder parsed — matches sample_statement.csv spec."""
    import pathlib
    sample = pathlib.Path(__file__).parent.parent.parent / "docs" / "sample_statement.csv"
    result = svc.parse(sample.read_bytes())
    assert len(result.ignored_rows) == 2
    assert len(result.skipped_rows) == 4
    # 35 total data rows (incl. header), 36 lines; 2 ignored + 4 skipped = 6 removed, rest parsed
    assert len(result.rows) == 35 - 2 - 4  # 29 clean rows
