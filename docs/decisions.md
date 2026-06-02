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

## Summary service reuses `list_transactions` for filtering
`summary.compute()` calls `list_transactions(db, category=, month=, search=)` rather than duplicating the three filter clauses. The filter logic is non-trivial (SQLite `strftime`, `ilike`) and lives in one place. The minor cost — `list_transactions` also applies an `ORDER BY` that the aggregation doesn't need — is irrelevant at this scale.

## Python aggregation in `summary.compute`, not SQL GROUP BY
Aggregation is done by iterating the filtered transaction list in Python rather than with SQL `GROUP BY`. The dataset is small, the logic is clear and easy to test, and avoiding raw SQL keeps the service consistent with the rest of the codebase. Revisit only if performance becomes a concern.

## `test_categorize.py` instead of `test_category.py`
The test file for categorization logic is named `test_categorize.py` rather than the `test_category.py` listed in tasks.md. The verb form better describes what the file tests (the act of categorizing), avoids collision with the service module name `category.py`, and makes the file's purpose unambiguous.

## Frontend is a pure SPA (`ssr: false`)
`nuxt.config.ts` sets `ssr: false`. This is a local dev tool with no SEO requirements, and all data fetching is done against a local FastAPI server. Disabling SSR avoids the entire `useNuxtApp()` / server-context complexity for `$fetch` and `useRuntimeConfig`, making composables straightforward.

## `$fetch` for all API calls, not `useFetch`
All API calls in composables and pages use `$fetch` (ofetch) directly rather than Nuxt's `useFetch`. With `ssr: false`, both work identically. `$fetch` was chosen because it returns a plain Promise, which is simpler to compose with `async/await` in imperative functions like `uploadStatement` and `patchCategory`. `useFetch` would only add value if SSR caching or auto-deduplication were needed.

## TypeScript types defined manually in `types/api.ts`
API types are hand-written against the Pydantic schemas rather than generated (e.g. via openapi-typescript). The schema is small and stable; code generation would add a build step and tooling dependency for no real benefit at this scale. Pydantic v2 serializes `Decimal` as strings in JSON mode, so Decimal fields are typed as `string`.

## Loading states use text + disabled button, not visual spinner/skeleton
The import page shows "Importing…" button text; the summary page shows "Loading…" text. These fulfil the loading-state requirement at the MVP level without adding a spinner library or skeleton component. A visual spinner or skeleton can be added as polish without changing the surrounding logic.

## No pagination on `/transactions`
The sample dataset is small. A `limit/offset` query param can be added later if needed; building it now is premature.
