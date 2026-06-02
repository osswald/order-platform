<template>
  <div class="event-collective-tab">
    <div class="section-toolbar">
      <v-btn variant="outlined" type="button" :disabled="loading" @click="load">Aktualisieren</v-btn>
    </div>
    <p v-if="loadError" class="error">{{ loadError }}</p>
    <p v-else-if="loading" class="muted">Laden…</p>
    <template v-else-if="data">
      <p v-if="!data.payment_batches.length" class="muted">Noch keine Zahlungsbatches synchronisiert.</p>
      <VqDataTable v-else :headers="headers" :items="data.payment_batches" item-value="uuid" hide-default-footer class="vq-data-table list-table nested">
        <template #item.status="{ item }">{{ statusLabel(item.status) }}</template>
        <template #item.total_cents="{ item }">{{ formatMoney(item.total_cents) }}</template>
        <template #item.created_at="{ item }">{{ formatTime(item.created_at) }}</template>
      </VqDataTable>
    </template>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { apiFetch } from '../api'
import { formatAmount } from '../utils/money'
import VqDataTable from './VqDataTable.vue'

const props = defineProps({ eventId: { type: Number, required: true } })
const headers = [
  { title: 'Name', key: 'name' },
  { title: 'Status', key: 'status' },
  { title: 'Total', key: 'total_cents', align: 'end' },
  { title: 'Erstellt', key: 'created_at' },
]
const loading = ref(false)
const loadError = ref('')
const data = ref(null)

function formatMoney(cents) {
  return `${formatAmount(cents)} ${data.value?.currency || 'CHF'}`
}
function formatTime(iso) {
  if (!iso) return '—'
  try { return new Date(iso).toLocaleString('de-CH') } catch { return iso }
}
function statusLabel(v) {
  const s = String(v || '').toLowerCase()
  if (s === 'closed' || s === 'paid') return 'Abgeschlossen'
  if (s === 'open') return 'Offen'
  return v || '—'
}

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const resp = await apiFetch(`/events/${props.eventId}/payment-batches-v3`)
    if (!resp.ok) throw new Error(await resp.text())
    data.value = await resp.json()
  } catch (e) {
    loadError.value = e.message || 'Laden fehlgeschlagen'
    data.value = null
  } finally {
    loading.value = false
  }
}

watch(() => props.eventId, load, { immediate: true })
</script>
