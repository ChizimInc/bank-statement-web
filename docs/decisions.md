# Architecture Decisions & Simplifications

## Sync SQLAlchemy over async
Using synchronous SQLAlchemy sessions. Async adds complexity (session scoping, `asyncio` driver) with no practical benefit at this scale. Revisit only if concurrent imports become a requirement.

## Single signed `amount` column
Debit and Credit are separate CSV columns but are merged into one signed decimal on parse (`credit > 0`, `debit < 0`). Storing both raw columns would be overkill for a summary dashboard — the signed single field covers all aggregation needs.

## No Alembic
`Base.metadata.create_all` on startup is sufficient for a take-home with a fixed schema. Alembic adds a migration layer that has no practical benefit here — if the schema changes during development, dropping and recreating the SQLite file is faster.

## No auth / multi-user
Out of scope. All data is single-tenant. Adding auth would require sessions, JWT, or OAuth — none of which are relevant to the assignment goals.

## No deployment or CI config
Docker, GitHub Actions, and environment management are omitted. The app runs with `uvicorn` + `npm run dev` locally.

## Rules stored in DB, not config files
A file-based rules config (e.g., YAML) would be simpler to seed but harder to edit at runtime. DB-backed rules allow the frontend rules page to work without a server restart.

## Single import endpoint, no upload preview step
The earlier plan had a two-step upload → preview → confirm flow. That is unnecessary complexity: the assignment asks to surface imported vs. skipped counts, not a confirmation screen. `POST /import` parses, persists, and returns the result in one call.

## `useTransactions` composable scope
The composable covers upload state, the transaction list, and filter params. It does not abstract rules or summary — those pages are simple enough that inline `useFetch` calls are clearer than a dedicated composable.

## SHA256 dedup hash includes value_date, reference, and currency
The hash covers `date|value_date|description|reference|amount|currency`. The earlier plan used only `date|description|amount`, which risks false positives (two legitimate transactions on the same day for the same amount from the same merchant). The wider key still catches the exact duplicate in the sample (rows 24 and 25 are identical on all six fields) while avoiding incorrect skips. `value_date` and `reference` are also stored on the `Transaction` model because they are useful for audit and debugging, not just deduplication.

## No currency conversion
Summary totals are grouped per currency (MDL, EUR, USD) and never combined into a single figure. The assignment provides no exchange-rate source, so cross-currency aggregation would require fabricating a rate. Showing separate per-currency totals is accurate and honest.

## Manual overrides are not protected from /rules/apply
`PATCH /transactions/{id}` writes a category override directly to the row. If the user later runs `POST /rules/apply`, that override is silently overwritten by whatever the rules produce. The UI must warn the user before they apply rules. This is intentional: rules are the authoritative source of truth; a manual override that the user wants to keep permanently should be saved as a rule.

## Save-as-rule proposes an editable pattern, not the full description
When saving a manual override as a rule, the UI derives a short proposed pattern from the description (e.g. `ORANGE` from `ORANGE MOLDOVA SA ABONAMENT MOBIL`) and lets the user edit it before saving. Auto-saving the full description as a rule would create an overly narrow rule that matches only one transaction. The editable proposal trades one extra interaction for a meaningfully reusable rule.

## `test_categorize.py` instead of `test_category.py`
The test file for categorization logic is named `test_categorize.py` rather than the `test_category.py` listed in tasks.md. The verb form better describes what the file tests (the act of categorizing), avoids collision with the service module name `category.py`, and makes the file's purpose unambiguous.

## No pagination on `/transactions`
The sample dataset is small. A `limit/offset` query param can be added later if needed; building it now is premature.
