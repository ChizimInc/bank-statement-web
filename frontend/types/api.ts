// Pydantic v2 serializes Decimal fields as strings in JSON mode.

export interface TransactionOut {
  id: number
  date: string
  value_date: string | null
  description: string
  reference: string | null
  amount: string
  currency: string
  category: string
  dedup_hash: string
}

export interface SkippedRow {
  source_line: number
  statement_nr: string | null
  reason: string
}

export interface IgnoredRow {
  source_line: number
  statement_nr: string | null
  reason: string
}

export interface ImportResult {
  imported: number
  skipped: number
  ignored: number
  skipped_rows: SkippedRow[]
  ignored_rows: IgnoredRow[]
  transactions: TransactionOut[]
}

export interface RuleOut {
  id: number
  pattern: string
  category: string
  priority: number
}

export interface CategoryBreakdown {
  category: string
  income: string
  spending: string
  balance: string
}

export interface CurrencySummary {
  currency: string
  income: string
  spending: string
  balance: string
  by_category: CategoryBreakdown[]
}

export interface SummaryOut {
  currencies: CurrencySummary[]
}

export interface TransactionFilters {
  category?: string
  month?: string
  search?: string
}
