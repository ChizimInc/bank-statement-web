<script setup lang="ts">
import type { ImportResult } from '~/types/api'

const { transactions, loading, error, uploadStatement } = useTransactions()

const file = ref<File | null>(null)
const result = ref<ImportResult | null>(null)

function handleFile(e: Event) {
  const input = e.target as HTMLInputElement
  file.value = input.files?.[0] ?? null
  result.value = null
}

async function upload() {
  if (!file.value) return
  result.value = await uploadStatement(file.value)
}
</script>

<template>
  <div>
    <h1 class="text-xl font-bold mb-4">Import Bank Statement</h1>

    <!-- Upload controls -->
    <div class="flex items-center gap-3 mb-6">
      <label class="cursor-pointer px-4 py-2 border rounded bg-white text-sm hover:bg-gray-50 text-gray-700">
        {{ file ? file.name : 'Choose CSV file' }}
        <input type="file" accept=".csv" class="hidden" @change="handleFile" />
      </label>
      <button
        @click="upload"
        :disabled="!file || loading"
        class="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50"
      >
        {{ loading ? 'Importing…' : 'Import' }}
      </button>
    </div>

    <!-- Error -->
    <div v-if="error" role="alert" class="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded text-sm">
      {{ error }}
    </div>

    <!-- Import result -->
    <template v-if="result">
      <div class="flex gap-6 mb-3 text-sm">
        <span class="text-green-600 font-medium">Imported: {{ result.imported }}</span>
        <span class="text-yellow-600 font-medium">Skipped: {{ result.skipped }}</span>
        <span class="text-gray-400">Ignored: {{ result.ignored }}</span>
      </div>

      <details v-if="result.skipped_rows.length" class="mb-2 text-sm">
        <summary class="cursor-pointer text-yellow-700 hover:underline select-none">
          {{ result.skipped_rows.length }} skipped row(s)
        </summary>
        <ul class="mt-1 pl-4 text-gray-600 space-y-0.5 text-xs">
          <li v-for="row in result.skipped_rows" :key="row.source_line">
            Line {{ row.source_line }}: {{ row.reason }}
          </li>
        </ul>
      </details>

      <details v-if="result.ignored_rows.length" class="mb-4 text-sm">
        <summary class="cursor-pointer text-gray-400 hover:underline select-none">
          {{ result.ignored_rows.length }} ignored row(s)
        </summary>
        <ul class="mt-1 pl-4 text-gray-400 space-y-0.5 text-xs">
          <li v-for="row in result.ignored_rows" :key="row.source_line">
            Line {{ row.source_line }}: {{ row.reason }}
          </li>
        </ul>
      </details>

      <TransactionTable :transactions="transactions" />
    </template>

    <!-- Empty state -->
    <p v-else-if="!loading" class="text-gray-400 text-sm">
      No transactions yet — upload a CSV to get started.
    </p>
  </div>
</template>
