# Bank Statement Web

A fullstack tool for importing, categorizing, and summarizing bank CSV statements.

---

## Main features

- CSV import with robust parsing
- Broken row reporting (skipped / ignored counts with per-row reasons)
- Duplicate detection (within file and across imports)
- Rule-based categorization (priority-ordered, case-insensitive)
- Manual category override per transaction
- Optional save-as-rule from a manual override
- Re-apply all rules to stored transactions
- Transaction table with category / month / search filters
- Summary grouped by currency and category (MDL, EUR, USD never mixed)

---

## Prerequisites

- Python 3.x
- Node.js 20+
- npm / pnpm
- SQLite

---

## Running the backend

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate        # Windows; use source .venv/bin/activate on Mac/Linux
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API is available at `http://localhost:8000`. Health check: `GET /`.

## Running the frontend

```bash
cd frontend
npm install
npm run dev
```

The app is available at `http://localhost:3000`.

---

## Checks

**Backend tests:**

```bash
cd backend
pytest
```

**Frontend lint & type-check:**

```bash
cd frontend
npm run lint
npm run typecheck
```

---

## Architecture

```
CSV upload
    └─► ParseService          – scans for header, skips balance rows, validates dates/amounts,
    |                           deduplicates within the file, returns ParseResult
    └─► ImportEndpoint        – checks DB for cross-import duplicates, calls CategoryService,
    |                           bulk-inserts, returns ImportResult
    └─► CategoryService       – matches description against DB rules (priority-ordered,
                                case-insensitive), assigns category or "Uncategorized"

Rules CRUD   ─► POST /rules/apply  ─► CategoryService.categorize_all – re-runs all rules
                                                                        on every stored transaction

GET /summary ─► SummaryService    – groups transactions by currency (MDL / EUR / USD kept
                                    separate), computes income / spending / balance per currency
                                    and per category; accepts category / month / search filters
```

**Storage:** SQLite via SQLAlchemy (synchronous). Schema created at startup; no migrations needed.

---

## Sample import (`docs/sample_statement.csv`)

| Outcome  | Count | Rows                                     | Reason                            |
|----------|-------|------------------------------------------|-----------------------------------|
| Ignored  | 2     | row 1, row 35                            | Balance summary rows (SOLD INITIAL / SOLD FINAL) |
| Skipped  | 4     | row 16, row 20, row 23, row 25           | Missing fields / invalid amount / invalid date+amount / duplicate |
| Imported | 29    | all remaining rows                       | Parsed cleanly with signed amounts and currencies |

---

## How I built this with AI

This project was built almost entirely through an iterative AI-assisted workflow using Claude Code.

**Tools used:** Claude Code (CLI) as the primary development agent, with the Anthropic API (claude-sonnet-4-6) driving every code generation step.

**How work was split:** Each feature area — backend scaffold, parser, CRUD endpoints, summary service, frontend pages, composables, tests — was tackled as a separate conversation turn with a focused prompt. The AI proposed the implementation; I reviewed the diff, ran the tests, and either accepted the output or gave corrective feedback.

**What prompts were kept vs. rewritten:** Most single-task prompts ("write a pytest for the parse service") worked well on the first pass. Prompts for cross-cutting concerns ("add currency grouping that never mixes MDL and EUR") required more back-and-forth to get the right data model.

**One concrete example where the AI was wrong:**
The first version of the dedup hash only covered `date|description|amount`. I caught that this would produce false positives for two legitimate transactions on the same day for the same amount from the same merchant (e.g., two identical top-up charges). I overruled it and specified a wider key: `date|value_date|description|reference|amount|currency`. The AI had optimized for the minimal key that covered the sample file; I had to supply the real-world constraint.

---

## Assignment evidence

- **Plan:** [docs/plan.md](docs/plan.md)
- **AI-reviewed PR:**
- **Public repo:** https://github.com/ChizimInc/bank-statement-web