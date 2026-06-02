<script setup lang="ts">
import type { SummaryOut } from '~/types/api'

const config = useRuntimeConfig()
const base = config.public.apiBase

const { transactions, fetchTransactions, patchCategory } = useTransactions()

const summary = ref<SummaryOut | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

const filters = reactive({ search: '', month: '', category: '' })

async function fetchData() {
  loading.value = true
  error.value = null
  const params = new URLSearchParams()
  if (filters.search) params.set('search', filters.search)
  if (filters.month) params.set('month', filters.month)
  if (filters.category) params.set('category', filters.category)
  const q = params.toString() ? `?${params}` : ''
  try {
    const [summaryData] = await Promise.all([
      $fetch<SummaryOut>(`${base}/summary${q}`),
      fetchTransactions({ ...filters }),
    ])
    summary.value = summaryData
  } catch {
    error.value = 'Failed to load data. Is the backend running?'
  } finally {
    loading.value = false
  }
}

async function onPatch(id: number, category: string, saveAsRule: boolean, pattern: string) {
  await patchCategory(id, category, saveAsRule, pattern)
  await fetchData()
}

function resetFilters() {
  filters.search = ''
  filters.month = ''
  filters.category = ''
}

function fmt(val: string): string {
  return parseFloat(val).toFixed(2)
}

function fmtAbs(val: string): string {
  return Math.abs(parseFloat(val)).toFixed(2)
}

function balanceClass(val: string): string {
  return parseFloat(val) >= 0 ? 'text-green-600' : 'text-red-500'
}

onMounted(fetchData)

let debounceTimer: ReturnType<typeof setTimeout>
watch(filters, () => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(fetchData, 300)
}, { deep: true })
</script>

<template>
  <div>
    <h1 class="text-xl font-bold mb-4">Summary</h1>

    <!-- Filters -->
    <div class="flex gap-3 mb-6 text-sm flex-wrap">
      <input
        v-model="filters.search"
        placeholder="Search description..."
        class="border rounded px-3 py-1.5 flex-1 min-w-40 focus:outline-none focus:ring-1 focus:ring-blue-400"
      />
      <input
        v-model="filters.month"
        type="month"
        class="border rounded px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-400"
      />
      <input
        v-model="filters.category"
        placeholder="Category..."
        class="border rounded px-3 py-1.5 w-36 focus:outline-none focus:ring-1 focus:ring-blue-400"
      />
      <button
        @click="resetFilters"
        class="px-3 py-1.5 bg-gray-200 rounded hover:bg-gray-300 text-xs text-gray-600"
      >
        Clear
      </button>
    </div>

    <!-- Skeleton loader -->
    <div v-if="loading" class="grid gap-4 mb-6" aria-busy="true" aria-label="Loading summary">
      <div v-for="i in 2" :key="i" class="bg-white border rounded-lg p-4 animate-pulse">
        <div class="h-4 bg-gray-200 rounded w-16 mb-3"></div>
        <div class="flex gap-8">
          <div>
            <div class="h-3 bg-gray-100 rounded w-10 mb-1.5"></div>
            <div class="h-4 bg-gray-200 rounded w-20"></div>
          </div>
          <div>
            <div class="h-3 bg-gray-100 rounded w-14 mb-1.5"></div>
            <div class="h-4 bg-gray-200 rounded w-20"></div>
          </div>
          <div>
            <div class="h-3 bg-gray-100 rounded w-12 mb-1.5"></div>
            <div class="h-4 bg-gray-200 rounded w-20"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- Error -->
    <div v-if="error" role="alert" class="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded text-sm">
      {{ error }}
    </div>

    <!-- Currency stat cards -->
    <div v-if="summary && summary.currencies.length" class="grid gap-4 mb-6">
      <div
        v-for="cur in summary.currencies"
        :key="cur.currency"
        class="bg-white border rounded-lg p-4"
      >
        <h2 class="font-bold text-base mb-2 text-gray-800">{{ cur.currency }}</h2>
        <div class="flex gap-8 text-sm mb-3">
          <div>
            <span class="text-gray-400 text-xs block">Income</span>
            <span class="font-mono text-green-600">{{ fmt(cur.income) }}</span>
          </div>
          <div>
            <span class="text-gray-400 text-xs block">Spending</span>
            <span class="font-mono text-red-500">{{ fmtAbs(cur.spending) }}</span>
          </div>
          <div>
            <span class="text-gray-400 text-xs block">Balance</span>
            <span class="font-mono font-medium" :class="balanceClass(cur.balance)">{{ fmt(cur.balance) }}</span>
          </div>
        </div>

        <details class="text-xs">
          <summary class="cursor-pointer text-gray-400 hover:text-gray-600 select-none">
            By category ({{ cur.by_category.length }})
          </summary>
          <table class="mt-2 w-full">
            <thead>
              <tr class="text-gray-400">
                <th class="text-left py-1 pr-4 font-normal">Category</th>
                <th class="text-right py-1 pr-4 font-normal">Income</th>
                <th class="text-right py-1 pr-4 font-normal">Spending</th>
                <th class="text-right py-1 font-normal">Balance</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="cat in cur.by_category" :key="cat.category" class="border-t border-gray-100">
                <td class="py-1 pr-4 text-gray-600">{{ cat.category }}</td>
                <td class="py-1 pr-4 text-right font-mono text-green-600">{{ fmt(cat.income) }}</td>
                <td class="py-1 pr-4 text-right font-mono text-red-500">{{ fmtAbs(cat.spending) }}</td>
                <td class="py-1 text-right font-mono" :class="balanceClass(cat.balance)">{{ fmt(cat.balance) }}</td>
              </tr>
            </tbody>
          </table>
        </details>
      </div>
    </div>

    <div v-else-if="summary && !summary.currencies.length && !loading" class="text-gray-400 text-sm mb-6">
      No transactions match the current filters.
    </div>

    <!-- Transaction table with inline category edit -->
    <h2 class="font-semibold text-sm text-gray-500 mb-2 uppercase tracking-wide">Transactions</h2>
    <TransactionTable
      :transactions="transactions"
      :editable="true"
      @patch="onPatch"
    />
  </div>
</template>
