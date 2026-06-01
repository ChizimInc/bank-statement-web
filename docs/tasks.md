# Build Checklist

## 1. Repo Setup
- [ ] Confirm monorepo layout: `backend/`, `frontend/`, `docs/`
- [ ] Add root `.gitignore` (Python venv, `__pycache__`, `*.db`, Node `node_modules`, `.nuxt`)
- [ ] Add `README.md` skeleton — fill in at the end

---

## 2. Backend Scaffold
- [ ] `python -m venv .venv` inside `backend/`
- [ ] Install: `fastapi`, `uvicorn[standard]`, `sqlalchemy`, `pydantic>=2`, `python-multipart`
- [ ] `app/db.py` — SQLite engine, `SessionLocal`, `Base`; call `Base.metadata.create_all` on startup
- [ ] `app/models/transaction.py` — `Transaction` ORM model (`id, date, value_date, description, reference, amount, currency, category, dedup_hash`)
- [ ] `app/models/rule.py` — `CategoryRule` ORM model (`id, pattern, category, priority`)
- [ ] `app/schemas/` — Pydantic v2 schemas using `model_config = ConfigDict(from_attributes=True)` (not v1 `orm_mode`):
  - `TransactionOut`, `RuleIn`, `RuleOut`
  - `SkippedRow(source_line, statement_nr, reason)`, `IgnoredRow(source_line, statement_nr, reason)` — `source_line` is the physical CSV line; `statement_nr` is the value from the `Nr` column when present
  - `ImportResult(imported, skipped, ignored, skipped_rows, ignored_rows, transactions)`
- [ ] `app/main.py` — create app, register routers, add CORS middleware
- [ ] Smoke test: `GET /` returns `{"status": "ok"}`

---

## 3. Parser Service
- [ ] `app/services/parse.py` — `ParseService.parse(file_bytes: bytes) -> ParseResult`
- [ ] Scan rows to find header line containing `Descriere`; discard everything before it
- [ ] **Ignore** balance rows (`SOLD INITIAL`, `SOLD FINAL`) — record in `ignored_rows` with reason `"Balance summary row"`
- [ ] Strip space thousand-separators; replace `,` decimal with `.`
- [ ] Parse `DD.MM.YYYY` with `datetime.strptime`; add to `skipped_rows` with reason `"Invalid date"` if unparseable (sample: row 23 has `abc`)
- [ ] Merge Debit / Credit into a single signed `Decimal` (debit → negative, credit → positive); add to `skipped_rows` with reason `"Missing or invalid amount"` if both are absent or non-numeric (sample: row 20 has no amounts, row 23 has `not_a_number`)
- [ ] Add to `skipped_rows` with reason `"Missing description and amount"` for rows with neither (sample: row 16)
- [ ] Compute `dedup_hash = SHA256(date|value_date|description|reference|amount|currency)` for each valid row; track in a `seen_hashes` set to catch duplicates **within the same file** — add to `skipped_rows` with reason `"Duplicate transaction"` before the DB is touched
- [ ] Each row appears **at most once** in `skipped_rows` — if multiple validations fail, combine the reasons (e.g. `"Invalid date and invalid amount"`)
- [ ] Return `ParseResult(rows, skipped_rows, ignored_rows)`
- [ ] Verify against `sample_statement.csv`:
  - 2 ignored rows: row 1 (`SOLD INITIAL`), row 35 (`SOLD FINAL`)
  - 4 skipped rows: row 16 (missing fields), row 20 (missing amounts), row 23 (invalid date + amount), row 25 (duplicate of row 24)
  - Remaining rows parsed cleanly with correct signed amounts and currencies

---

## 4. Import Endpoint
- [ ] `app/routers/import_.py` — `POST /import`, accepts `UploadFile` (multipart)
- [ ] Call `ParseService.parse(await file.read())`
- [ ] For each parsed row from `ParseResult.rows`, check `dedup_hash` against the DB to catch **cross-import duplicates** (intra-file duplicates are already caught by `ParseService`); add to `skipped_rows` with reason `"Duplicate transaction"`
- [ ] Apply `CategoryService.categorize(description, rules)` to each row before insert
- [ ] Bulk-insert valid transactions
- [ ] Return `ImportResult(imported=N, skipped=M, ignored=K, skipped_rows=[...], ignored_rows=[...], transactions=[...])`

---

## 5. Rules CRUD
- [ ] `app/routers/rules.py` — `GET /rules`, `POST /rules`, `PUT /rules/{id}`, `DELETE /rules/{id}`
- [ ] `app/services/category.py` — `CategoryService`
  - [ ] `categorize(description: str, rules: list[CategoryRule]) -> str` — ordered by `priority`, case-insensitive contains match, fallback `"Uncategorized"`
  - [ ] `categorize_all(db: Session)` — re-runs rules on every transaction in DB, bulk-updates categories

---

## 6. Recategorization & Manual Override
- [ ] `POST /rules/apply` — calls `CategoryService.categorize_all(db)`, returns `{updated: N}`
- [ ] `PATCH /transactions/{id}` — body: `{category: str, save_as_rule?: bool, pattern?: str}`
  - If `save_as_rule` is false or absent, the manual change may be overwritten by future `/rules/apply` calls
  - If `save_as_rule` is true, use the provided `pattern` (user-edited in UI) to insert a new `CategoryRule`

---

## 7. Summary Endpoint
- [ ] `app/services/summary.py` — `SummaryService.compute(db, *, category=None, month=None, search=None) -> SummaryOut`
  - [ ] Apply any provided filters before aggregating
  - [ ] Group all amounts by currency — **never add MDL + EUR + USD together**
  - [ ] Per currency: total income (sum of positive), total spending (sum of negative), balance
  - [ ] Per-category breakdown also grouped by currency
- [ ] `GET /summary` — optional query params: `category` (str), `month` (YYYY-MM), `search` (str); computes summary for the filtered transaction set when provided, all transactions otherwise; always grouped per currency
- [ ] `GET /transactions` — query params: `category` (str), `month` (YYYY-MM), `search` (str)

---

## 8. Frontend Pages
- [ ] `npx nuxi init frontend` — select Tailwind CSS during setup
- [ ] Set `NUXT_PUBLIC_API_BASE=http://localhost:8000` in `.env` and `nuxt.config.ts` `runtimeConfig`
- [ ] `pages/index.vue`
  - [ ] File input + upload button
  - [ ] After upload, show **imported / skipped / ignored** counts
  - [ ] Show `skipped_rows` and `ignored_rows` details in a collapsible panel (row number + reason)
  - [ ] Render `TransactionTable` with results
- [ ] `pages/rules.vue`
  - [ ] List rules with edit/delete per row; inline add-rule form
  - [ ] "Apply Rules" button with a confirmation: **"This will overwrite any manual category changes"**
- [ ] `pages/summary.vue`
  - [ ] Stat cards grouped by currency (MDL, EUR, USD — no mixing)
  - [ ] `TransactionTable` with category, month, search filters
  - [ ] Inline category edit per row with "Save as rule" option that opens an editable pattern field

---

## 9. Composables
- [ ] `composables/useTransactions.ts`
  - [ ] `transactions` (ref), `loading` (ref), `error` (ref)
  - [ ] `fetchTransactions(filters?)` — calls `GET /transactions`, populates `transactions`
  - [ ] `uploadStatement(file: File)` — calls `POST /import`, returns `ImportResult`, then refreshes list
  - [ ] `patchCategory(id, category, saveAsRule?, pattern?)` — calls `PATCH /transactions/{id}`, updates local state; if `saveAsRule`, pass the user-edited `pattern`

---

## 10. Loading / Empty / Error States
- [ ] Import page: spinner while upload is in-flight; "No transactions yet — upload a CSV to get started" empty state
- [ ] Rules page: "No rules defined yet" empty state with a prompt to add the first rule
- [ ] Summary page: skeleton loader while fetching; error banner (`<div role="alert">`) on API failure
- [ ] All submit buttons disabled while request is in-flight

---

## 11. Backend Tests
- [ ] `tests/test_parse.py`
  - [ ] Parses `DD.MM.YYYY` dates correctly
  - [ ] Normalizes amounts: strips space thousand-separators, replaces `,` decimal with `.`
  - [ ] Debit becomes negative, credit becomes positive
  - [ ] Row with invalid date is skipped with reason `"Invalid date"`
  - [ ] Row with missing/invalid amount is skipped with reason `"Missing or invalid amount"`
  - [ ] `SOLD INITIAL` / `SOLD FINAL` rows are ignored with reason `"Balance summary row"`
  - [ ] Duplicate row is skipped during import with reason `"Duplicate transaction"`
- [ ] `tests/test_category.py`
  - [ ] Match is case-insensitive
  - [ ] Priority order respected — first matching rule wins
  - [ ] No match returns `"Uncategorized"`
- [ ] `tests/test_summary.py`
  - [ ] Summary groups results per currency
  - [ ] MDL, EUR, and USD totals are never combined into one value
  - [ ] Summary filtered by month returns correct per-currency totals for that subset only

---

## 12. Final Cleanup & README
- [ ] Fill `README.md`:
  - [ ] How to run backend: `cd backend && uvicorn app.main:app --reload` (≤5 commands)
  - [ ] How to run frontend: `cd frontend && npm install && npm run dev` (≤5 commands)
  - [ ] Architecture overview: services, data flow, import → categorize → summary
  - [ ] Sample import behavior: expected ignored / skipped / imported counts for `sample_statement.csv`
  - [ ] "How I built this with AI" — tools used, how work was split, what prompts were kept vs. rewritten
  - [ ] One concrete example where the AI was wrong and why it was overruled
- [ ] Open a PR for a meaningful slice of work; run through an AI code reviewer; address comments; leave review visible
- [ ] Verify clean git history — small, meaningful commits, no single giant dump
