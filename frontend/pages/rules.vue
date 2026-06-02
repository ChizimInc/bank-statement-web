<script setup lang="ts">
import type { RuleOut } from '~/types/api'

const config = useRuntimeConfig()
const base = config.public.apiBase

const rules = ref<RuleOut[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const applyMsg = ref<string | null>(null)

const newRule = reactive({ pattern: '', category: '', priority: 0 })
const editingId = ref<number | null>(null)
const editForm = reactive({ pattern: '', category: '', priority: 0 })

async function fetchRules() {
  try {
    rules.value = await $fetch<RuleOut[]>(`${base}/rules`)
  } catch {
    error.value = 'Failed to load rules'
  }
}

async function addRule() {
  if (!newRule.pattern.trim() || !newRule.category.trim()) return
  error.value = null
  try {
    await $fetch(`${base}/rules`, { method: 'POST', body: { ...newRule } })
    Object.assign(newRule, { pattern: '', category: '', priority: 0 })
    await fetchRules()
  } catch {
    error.value = 'Failed to add rule'
  }
}

function startEdit(rule: RuleOut) {
  editingId.value = rule.id
  Object.assign(editForm, { pattern: rule.pattern, category: rule.category, priority: rule.priority })
}

async function saveEdit(id: number) {
  error.value = null
  try {
    await $fetch(`${base}/rules/${id}`, { method: 'PUT', body: { ...editForm } })
    editingId.value = null
    await fetchRules()
  } catch {
    error.value = 'Failed to update rule'
  }
}

async function deleteRule(id: number) {
  error.value = null
  try {
    await $fetch(`${base}/rules/${id}`, { method: 'DELETE' })
    await fetchRules()
  } catch {
    error.value = 'Failed to delete rule'
  }
}

async function applyRules() {
  if (!confirm('Apply rules to all transactions? This will overwrite any manual category changes.')) return
  loading.value = true
  applyMsg.value = null
  error.value = null
  try {
    const res = await $fetch<{ updated: number }>(`${base}/rules/apply`, { method: 'POST' })
    applyMsg.value = `${res.updated} transaction(s) updated.`
  } catch {
    error.value = 'Failed to apply rules'
  } finally {
    loading.value = false
  }
}

onMounted(fetchRules)
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-4">
      <h1 class="text-xl font-bold">Categorization Rules</h1>
      <button
        @click="applyRules"
        :disabled="loading"
        class="px-4 py-2 bg-amber-500 text-white text-sm rounded hover:bg-amber-600 disabled:opacity-50"
      >
        {{ loading ? 'Applying…' : 'Apply Rules' }}
      </button>
    </div>

    <div v-if="applyMsg" class="mb-4 p-3 bg-green-50 border border-green-200 text-green-700 rounded text-sm">
      {{ applyMsg }}
    </div>
    <div v-if="error" role="alert" class="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded text-sm">
      {{ error }}
    </div>

    <!-- Add rule form -->
    <form @submit.prevent="addRule" class="flex gap-2 mb-6 text-sm">
      <input
        v-model="newRule.pattern"
        placeholder="Pattern (e.g. orange)"
        required
        class="border rounded px-3 py-1.5 flex-1 min-w-0 focus:outline-none focus:ring-1 focus:ring-blue-400"
      />
      <input
        v-model="newRule.category"
        placeholder="Category (e.g. Telecom)"
        required
        class="border rounded px-3 py-1.5 flex-1 min-w-0 focus:outline-none focus:ring-1 focus:ring-blue-400"
      />
      <input
        v-model.number="newRule.priority"
        type="number"
        placeholder="Priority"
        class="border rounded px-3 py-1.5 w-24 focus:outline-none focus:ring-1 focus:ring-blue-400"
      />
      <button type="submit" class="px-4 py-1.5 bg-blue-600 text-white rounded hover:bg-blue-700">
        Add
      </button>
    </form>

    <!-- Empty state -->
    <div v-if="!rules.length" class="text-gray-400 text-sm py-8 text-center">
      No rules defined yet — add one above to start categorizing transactions.
    </div>

    <!-- Rules table -->
    <table v-else class="w-full text-sm border-collapse">
      <thead>
        <tr class="border-b text-gray-500 font-medium text-xs uppercase tracking-wide">
          <th class="py-2 pr-4 text-left">Pattern</th>
          <th class="py-2 pr-4 text-left">Category</th>
          <th class="py-2 pr-4 text-left">Priority</th>
          <th class="py-2 text-left">Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="rule in rules" :key="rule.id" class="border-b hover:bg-gray-50">
          <template v-if="editingId === rule.id">
            <td class="py-2 pr-2">
              <input v-model="editForm.pattern" class="border rounded px-2 py-0.5 w-full text-sm focus:outline-none focus:ring-1 focus:ring-blue-400" />
            </td>
            <td class="py-2 pr-2">
              <input v-model="editForm.category" class="border rounded px-2 py-0.5 w-full text-sm focus:outline-none focus:ring-1 focus:ring-blue-400" />
            </td>
            <td class="py-2 pr-2">
              <input v-model.number="editForm.priority" type="number" class="border rounded px-2 py-0.5 w-20 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400" />
            </td>
            <td class="py-2 flex gap-1">
              <button @click="saveEdit(rule.id)" class="px-3 py-0.5 bg-blue-600 text-white rounded text-xs hover:bg-blue-700">Save</button>
              <button @click="editingId = null" class="px-3 py-0.5 bg-gray-200 rounded text-xs hover:bg-gray-300">Cancel</button>
            </td>
          </template>
          <template v-else>
            <td class="py-2 pr-4 font-mono text-xs">{{ rule.pattern }}</td>
            <td class="py-2 pr-4">{{ rule.category }}</td>
            <td class="py-2 pr-4 text-gray-500">{{ rule.priority }}</td>
            <td class="py-2 flex gap-1">
              <button @click="startEdit(rule)" class="px-3 py-0.5 bg-gray-200 rounded text-xs hover:bg-gray-300">Edit</button>
              <button @click="deleteRule(rule.id)" class="px-3 py-0.5 bg-red-100 text-red-600 rounded text-xs hover:bg-red-200">Delete</button>
            </td>
          </template>
        </tr>
      </tbody>
    </table>
  </div>
</template>
