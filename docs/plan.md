# Implementation Plan

## Architecture Outline
Nuxt 3 SPA → FastAPI REST API → SQLite (SQLAlchemy sync). Route handlers stay thin; CSV parsing lives in `ParseService`, categorization in `CategoryService`, aggregations in `SummaryService`. Frontend styled with Tailwind.

---

## File / Folder Structure
```
backend/
  app/
    models/       # SQLAlchemy ORM
    schemas/      # Pydantic v2 schemas
    services/     # parse.py, category.py, summary.py
    routers/      # import.py, transactions.py, rules.py, summary.py
    db.py         # engine, session, create_all on startup
    main.py
frontend/
  pages/
    index.vue     # import flow
    rules.vue     # manage category rules
    summary.vue   # dashboard + transaction table
  components/     # TransactionTable, RuleRow, StatCard
  composables/
    useTransactions.ts
docs/
```

---

## Backend Endpoints
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/import` | Parse + persist CSV; return `{imported, skipped, ignored, skipped_rows, ignored_rows, transactions}` |
| GET | `/transactions` | List; filter by `category`, `month`; search by `description` |
| PATCH | `/transactions/{id}` | Manual category override; optionally save as new rule |
| GET/POST/PUT/DELETE | `/rules` | CRUD category rules |
| POST | `/rules/apply` | Re-run all rules on stored transactions |
| GET | `/summary` | Income, spending, balance, per-category breakdown per currency; optional `category`, `month`, `search` filters narrow the transaction set before aggregation |

---

## Data Models
**Transaction**: `id, date, value_date, description, reference, amount, currency, category, dedup_hash`  
**CategoryRule**: `id, pattern, category, priority`

`amount` — single signed `Decimal`: debit → negative, credit → positive.  
`value_date` and `reference` stored for audit and debugging.  
`dedup_hash = SHA256(date|value_date|description|reference|amount|currency)` — catches the exact duplicate in the sample without false positives.

---

## Parsing Rules (`ParseService`)
The sample CSV has Romanian headers (`Nr, Data, Data valuta, Descriere, Referinta, Debit, Credit, Valuta`), broken rows, and one duplicate.

Terms: **ignored** = intentional non-transaction row; **skipped** = malformed or duplicate row.

1. Scan rows to find the header line (contains `Descriere`); discard everything before it.
2. **Ignore** balance rows (`SOLD INITIAL`, `SOLD FINAL`) — record with reason `"Balance summary row"`.
3. Strip space thousand-separators; replace `,` decimal with `.`
4. Parse `DD.MM.YYYY` via `strptime`; **skip** row with reason if unparseable (row 23: `abc`).
5. Merge Debit / Credit into signed amount; **skip** row with reason if both empty or non-numeric (row 20: no amounts; row 23: `not_a_number`).
6. **Skip** rows with no description and no amount (row 16).
7. Compute `dedup_hash`; **skip** if hash appears in the in-memory `seen_hashes` set (duplicate within the current batch) **or** already exists in the DB (cross-import duplicate); reason `"Duplicate transaction"` (row 25 = duplicate of row 24 in the sample).
8. Each row appears **at most once** in `skipped_rows`. If multiple validations fail, combine reasons (e.g. `"Invalid date and invalid amount"`). Each entry includes `source_line` (physical CSV line number) and `statement_nr` (value from the `Nr` column, when available) to avoid confusion between the two numbering schemes.
9. Return `{imported, skipped, ignored, skipped_rows, ignored_rows}` — all three counts shown in UI.

**Expected on sample file:** 2 ignored (source lines 2 and 36, balance rows), 4 skipped (source line 17: missing fields; line 21: missing amounts; line 24: invalid date and invalid amount; line 26: duplicate of line 25), remaining rows imported.

---

## Categorization Rules (`CategoryService`)
- Rule: `description.upper()` contains `pattern.upper()` → assign `category`. First match by `priority` wins.
- Default: `Uncategorized`.
- `POST /rules/apply` overwrites every transaction's category — **including manual overrides**. UI must warn the user before applying.
- `PATCH /transactions/{id}` allows manual override. Without `save_as_rule`, the override is lost on next `/rules/apply`.
- When `save_as_rule` is used, the UI proposes an **editable** pattern derived from the description before saving (e.g. `ORANGE MOLDOVA SA ABONAMENT MOBIL` → proposed pattern `ORANGE`, category `Telecom`).

---

## Milestone Plan
| # | Milestone |
|---|-----------|
| 1 | Backend scaffold — FastAPI, SQLAlchemy models, `create_all` on startup |
| 2 | `ParseService` — all CSV edge cases, verified against `sample_statement.csv` |
| 3 | `POST /import` — parse, deduplicate, persist, return imported/skipped/ignored |
| 4 | `CategoryService` + rules CRUD + `POST /rules/apply` |
| 5 | `SummaryService` + `GET /summary` (per-currency) + `GET /transactions` with filters |
| 6 | Nuxt scaffold + `useTransactions` composable + import page |
| 7 | Rules page + summary dashboard + loading / empty / error states |
