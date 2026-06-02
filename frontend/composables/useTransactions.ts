import type { ImportResult, TransactionFilters, TransactionOut } from '~/types/api'

export function useTransactions() {
  const config = useRuntimeConfig()
  const base = config.public.apiBase

  const transactions = ref<TransactionOut[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchTransactions(filters?: TransactionFilters) {
    loading.value = true
    error.value = null
    try {
      const params = new URLSearchParams()
      if (filters?.category) params.set('category', filters.category)
      if (filters?.month) params.set('month', filters.month)
      if (filters?.search) params.set('search', filters.search)
      const q = params.toString()
      transactions.value = await $fetch<TransactionOut[]>(
        `${base}/transactions${q ? '?' + q : ''}`,
      )
    } catch (e: unknown) {
      error.value = `Failed to load transactions: ${e instanceof Error ? e.message : String(e)}`
    } finally {
      loading.value = false
    }
  }

  async function uploadStatement(file: File): Promise<ImportResult | null> {
    loading.value = true
    error.value = null
    try {
      const form = new FormData()
      form.append('file', file)
      const result = await $fetch<ImportResult>(`${base}/import`, {
        method: 'POST',
        body: form,
      })
      await fetchTransactions()
      return result
    } catch (e: unknown) {
      error.value = `Upload failed: ${e instanceof Error ? e.message : String(e)}`
      return null
    } finally {
      loading.value = false
    }
  }

  async function patchCategory(
    id: number,
    category: string,
    saveAsRule = false,
    pattern?: string,
  ) {
    try {
      const body: Record<string, unknown> = { category }
      if (saveAsRule && pattern) {
        body.save_as_rule = true
        body.pattern = pattern
      }
      const updated = await $fetch<TransactionOut>(`${base}/transactions/${id}`, {
        method: 'PATCH',
        body,
      })
      const idx = transactions.value.findIndex(t => t.id === id)
      if (idx !== -1) transactions.value[idx] = updated
    } catch {
      error.value = 'Failed to update category'
    }
  }

  return { transactions, loading, error, fetchTransactions, uploadStatement, patchCategory }
}
