<script setup lang="ts">
import type { TransactionOut } from '~/types/api'

const props = withDefaults(defineProps<{
  transactions: TransactionOut[]
  editable?: boolean
}>(), { editable: false })

const emit = defineEmits<{
  patch: [id: number, category: string, saveAsRule: boolean, pattern: string]
}>()

type EditState = { category: string; saveAsRule: boolean; pattern: string }
const editing = ref<Record<number, EditState>>({})

function startEdit(tx: TransactionOut) {
  editing.value[tx.id] = { category: tx.category, saveAsRule: false, pattern: tx.description }
}

function cancelEdit(id: number) {
  delete editing.value[id]
}

function saveEdit(id: number) {
  const e = editing.value[id]
  emit('patch', id, e.category, e.saveAsRule, e.pattern)
  cancelEdit(id)
}

function fmt(amount: string): string {
  return parseFloat(amount).toFixed(2)
}

function amountClass(amount: string): string {
  return parseFloat(amount) >= 0 ? 'text-green-600' : 'text-red-500'
}
</script>

<template>
  <div v-if="transactions.length === 0" class="text-center text-gray-400 text-sm py-8">
    No transactions to display.
  </div>
  <div v-else class="overflow-x-auto">
    <table class="w-full text-sm text-left border-collapse">
      <thead>
        <tr class="border-b text-gray-500 font-medium text-xs uppercase tracking-wide">
          <th class="py-2 pr-4">Date</th>
          <th class="py-2 pr-4">Description</th>
          <th class="py-2 pr-4 text-right">Amount</th>
          <th class="py-2 pr-4">Currency</th>
          <th class="py-2 pr-4">Category</th>
          <th v-if="editable" class="py-2" />
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="tx in transactions"
          :key="tx.id"
          class="border-b hover:bg-gray-50"
        >
          <td class="py-2 pr-4 text-gray-400 whitespace-nowrap text-xs">{{ tx.date }}</td>
          <td class="py-2 pr-4 max-w-xs truncate" :title="tx.description">{{ tx.description }}</td>
          <td class="py-2 pr-4 text-right font-mono text-xs" :class="amountClass(tx.amount)">
            {{ fmt(tx.amount) }}
          </td>
          <td class="py-2 pr-4 text-xs text-gray-500">{{ tx.currency }}</td>

          <template v-if="!editable">
            <td class="py-2">
              <span class="px-2 py-0.5 bg-gray-100 rounded text-xs">{{ tx.category }}</span>
            </td>
          </template>

          <template v-else>
            <td class="py-2 pr-2">
              <template v-if="editing[tx.id]">
                <input
                  v-model="editing[tx.id].category"
                  class="border rounded px-2 py-0.5 text-xs w-32 focus:outline-none focus:ring-1 focus:ring-blue-400"
                />
              </template>
              <span v-else class="px-2 py-0.5 bg-gray-100 rounded text-xs">{{ tx.category }}</span>
            </td>
            <td class="py-2">
              <template v-if="editing[tx.id]">
                <div class="flex flex-col gap-1 min-w-max">
                  <label class="flex items-center gap-1 text-xs text-gray-500 cursor-pointer">
                    <input type="checkbox" v-model="editing[tx.id].saveAsRule" class="rounded" />
                    Save as rule
                  </label>
                  <input
                    v-if="editing[tx.id].saveAsRule"
                    v-model="editing[tx.id].pattern"
                    placeholder="Pattern..."
                    class="border rounded px-2 py-0.5 text-xs w-36 focus:outline-none focus:ring-1 focus:ring-blue-400"
                  />
                  <div class="flex gap-1">
                    <button
                      @click="saveEdit(tx.id)"
                      class="px-2 py-0.5 bg-blue-600 text-white rounded text-xs hover:bg-blue-700"
                    >Save</button>
                    <button
                      @click="cancelEdit(tx.id)"
                      class="px-2 py-0.5 bg-gray-200 rounded text-xs hover:bg-gray-300"
                    >Cancel</button>
                  </div>
                </div>
              </template>
              <button
                v-else
                @click="startEdit(tx)"
                class="px-2 py-0.5 bg-gray-200 rounded text-xs hover:bg-gray-300"
              >Edit</button>
            </td>
          </template>
        </tr>
      </tbody>
    </table>
  </div>
</template>
