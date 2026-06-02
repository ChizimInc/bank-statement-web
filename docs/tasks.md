# Build Checklist

## 1. Repo Setup
- [x] Confirm monorepo layout: `backend/`, `frontend/`, `docs/`
- [x] Add root `.gitignore` (Python venv, `__pycache__`, `*.db`, Node `node_modules`, `.nuxt`)
- [x] Add `README.md` skeleton — fill in at the end

---

## 2. Backend Scaffold
- [x] `python -m venv .venv` inside `backend/`
- [x] Install: `fastapi`, `uvicorn[standard]`, `sqlalchemy`, `pydantic>=2`, `python-multipart`
- [x] `app/db.py` — SQLite engine, `SessionLocal`, `Base`; call `Base.metadata.create_all` on startup
- [x] `app/models/transaction.py` — `Transaction` ORM model (`id, date, value_date, description, reference, amount, currency, category, dedup_hash`)
- [x] `app/models/rule.py` — `CategoryRule` ORM model (`id, pattern, category, priority`)
- [x] `app/schemas/` — Pydantic v2 schemas using `model_config = ConfigDict(from_attributes=True)` (not v1 `orm_mode`):
  - `TransactionOut`, `RuleIn`, `RuleOut`
  - `SkippedRow(source_line, statement_nr, reason)`, `IgnoredRow(source_line, statement_nr, reason)` — `source_line` is the physical CSV line; `statement_nr` is the value from the `Nr` column when present
  - `ImportResult(imported, skipped, ignored, skipped_rows, ignored_rows, transactions)`
- [x] `app/main.py` — create app, register routers, add CORS middleware
- [x] Smoke test: `GET /` returns `{"status": "ok"}` — verified by `tests/test_health.py` (4/4 pass)

---

## 3. Parser Service
- [x] `app/services/parse.py` — `ParseService.parse(file_bytes: bytes) -> ParseResult`
- [x] Scan rows to find header line containing `Descriere`; discard everything before it
- [x] **Ignore** balance rows (`SOLD INITIAL`, `SOLD FINAL`) — record in `ignored_rows` with reason `"Balance summary row"`
- [x] Strip space thousand-separators; replace `,` decimal with `.`
- [x] Parse `DD.MM.YYYY` with `datetime.strptime`; add to `skipped_rows` with reason `"Invalid date"` if unparseable (sample: row 23 has `abc`)
- [x] Merge Debit / Credit into a single signed `Decimal` (debit → negative, credit → positive); add to `skipped_rows` with reason `"Missing or invalid amount"` if both are absent or non-numeric (sample: row 20 has no amounts, row 23 has `not_a_number`)
- [x] Add to `skipped_rows` with reason `"Missing description and amount"` for rows with neither (sample: row 16)
- [x] Compute `dedup_hash = SHA256(date|value_date|description|reference|amount|currency)` for each valid row; track in a `seen_hashes` set to catch duplicates **within the same file** — add to `skipped_rows` with reason `"Duplicate transaction"` before the DB is touched
- [x] Each row appears **at most once** in `skipped_rows` — if multiple validations fail, combine the reasons (e.g. `"Invalid date and invalid amount"`)
- [x] Return `ParseResult(rows, skipped_rows, ignored_rows)`
- [x] Verify against `sample_statement.csv`:
  - 2 ignored rows: row 1 (`SOLD INITIAL`), row 35 (`SOLD FINAL`)
  - 4 skipped rows: row 16 (missing fields), row 20 (missing amounts), row 23 (invalid date + amount), row 25 (duplicate of row 24)
  - Remaining rows parsed cleanly with correct signed amounts and currencies

---

## 4. Import Endpoint
- [x] `app/routers/import_.py` — `POST /import`, accepts `UploadFile` (multipart)
- [x] Call `ParseService.parse(await file.read())`
- [x] For each parsed row from `ParseResult.rows`, check `dedup_hash` against the DB to catch **cross-import duplicates** (intra-file duplicates are already caught by `ParseService`); add to `skipped_rows` with reason `"Duplicate transaction"`
- [x] Apply `CategoryService.categorize(description, rules)` to each row before insert
- [x] Bulk-insert valid transactions
- [x] Return `ImportResult(imported=N, skipped=M, ignored=K, skipped_rows=[...], ignored_rows=[...], transactions=[...])`

---

## 5. Rules CRUD
- [x] `app/routers/rules.py` — `GET /rules`, `POST /rules`, `PUT /rules/{id}`, `DELETE /rules/{id}`
- [x] `app/services/category.py` — `CategoryService`
  - [x] `categorize(description: str, rules: list[CategoryRule]) -> str` — ordered by `priority`, case-insensitive contains match, fallback `"Uncategorized"`
  - [x] `categorize_all(db: Session)` — re-runs rules on every transaction in DB, bulk-updates categories

---

## 6. Recategorization & Manual Override
- [x] `POST /rules/apply` — calls `CategoryService.categorize_all(db)`, returns `{updated: N}`
- [x] `PATCH /transactions/{id}` — body: `{category: str, save_as_rule?: bool, pattern?: str}`
  - If `save_as_rule` is false or absent, the manual change may be overwritten by future `/rules/apply` calls
  - If `save_as_rule` is true, use the provided `pattern` (user-edited in UI) to insert a new `CategoryRule`

---

## 7. Summary Endpoint
- [x] `app/services/summary.py` — `SummaryService.compute(db, *, category=None, month=None, search=None) -> SummaryOut`
  - [x] Apply any provided filters before aggregating
  - [x] Group all amounts by currency — **never add MDL + EUR + USD together**
  - [x] Per currency: total income (sum of positive), total spending (sum of negative), balance
  - [x] Per-category breakdown also grouped by currency
- [x] `GET /summary` — optional query params: `category` (str), `month` (YYYY-MM), `search` (str); computes summary for the filtered transaction set when provided, all transactions otherwise; always grouped per currency
- [x] `GET /transactions` — query params: `category` (str), `month` (YYYY-MM), `search` (str)

---

## 8. Frontend Pages
- [x] `npx nuxi init frontend` — select Tailwind CSS during setup
- [x] Set `NUXT_PUBLIC_API_BASE=http://localhost:8000` in `.env` and `nuxt.config.ts` `runtimeConfig`
- [x] `pages/index.vue`
  - [x] File input + upload button
  - [x] After upload, show **imported / skipped / ignored** counts
  - [x] Show `skipped_rows` and `ignored_rows` details in a collapsible panel (row number + reason)
  - [x] Render `TransactionTable` with results
- [x] `pages/rules.vue`
  - [x] List rules with edit/delete per row; inline add-rule form
  - [x] "Apply Rules" button with a confirmation: **"This will overwrite any manual category changes"**
- [x] `pages/summary.vue`
  - [x] Stat cards grouped by currency (MDL, EUR, USD — no mixing)
  - [x] `TransactionTable` with category, month, search filters
  - [x] Inline category edit per row with "Save as rule" option that opens an editable pattern field

---

## 9. Composables
- [x] `composables/useTransactions.ts`
  - [x] `transactions` (ref), `loading` (ref), `error` (ref)
  - [x] `fetchTransactions(filters?)` — calls `GET /transactions`, populates `transactions`
  - [x] `uploadStatement(file: File)` — calls `POST /import`, returns `ImportResult`, then refreshes list
  - [x] `patchCategory(id, category, saveAsRule?, pattern?)` — calls `PATCH /transactions/{id}`, updates local state; if `saveAsRule`, pass the user-edited `pattern`

---

## 10. Loading / Empty / Error States
- [x] Import page: spinner while upload is in-flight; "No transactions yet — upload a CSV to get started" empty state
- [x] Rules page: "No rules defined yet" empty state with a prompt to add the first rule
- [ ] Summary page: skeleton loader while fetching; error banner (`<div role="alert">`) on API failure
  - [x] error banner with `role="alert"` implemented
  - [x] skeleton loader — animated pulse skeleton using Tailwind `animate-pulse`
- [ ] All submit buttons disabled while request is in-flight
  - [x] Import button and Apply Rules button are disabled during their respective requests
  - [x] Add Rule / Save Edit buttons disabled while in-flight (`addingRule` / `savingEditId` flags)

---

## 11. Backend Tests
- [x] `tests/test_parse.py`
  - [x] Parses `DD.MM.YYYY` dates correctly
  - [x] Normalizes amounts: strips space thousand-separators, replaces `,` decimal with `.`
  - [x] Debit becomes negative, credit becomes positive
  - [x] Row with invalid date is skipped with reason `"Invalid date"`
  - [x] Row with missing/invalid amount is skipped with reason `"Missing or invalid amount"`
  - [x] `SOLD INITIAL` / `SOLD FINAL` rows are ignored with reason `"Balance summary row"`
  - [x] Duplicate row is skipped during import with reason `"Duplicate transaction"`
- [x] `tests/test_categorize.py` (named `test_categorize.py` — see decisions.md)
  - [x] Match is case-insensitive
  - [x] Priority order respected — first matching rule wins
  - [x] No match returns `"Uncategorized"`
- [x] `tests/test_summary.py`
  - [x] Summary groups results per currency
  - [x] MDL, EUR, and USD totals are never combined into one value
  - [x] Summary filtered by month returns correct per-currency totals for that subset only

---

## 12. Final Cleanup & README
- [x] Fill `README.md`:
  - [x] How to run backend: `cd backend && uvicorn app.main:app --reload` (≤5 commands)
  - [x] How to run frontend: `cd frontend && npm install && npm run dev` (≤5 commands)
  - [x] Architecture overview: services, data flow, import → categorize → summary
  - [x] Sample import behavior: expected ignored / skipped / imported counts for `sample_statement.csv`
  - [x] "How I built this with AI" — tools used, how work was split, what prompts were kept vs. rewritten
  - [x] One concrete example where the AI was wrong and why it was overruled
