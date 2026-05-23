<template>
  <div>
    <h1>Offene Tische</h1>
    <p class="muted">{{ event?.name }}</p>

    <p v-if="loading" class="muted">Laden…</p>
    <div v-else-if="!tables.length" class="card">
      <p>Keine offenen Tische.</p>
      <button type="button" class="btn primary" @click="router.push({ name: 'hub' })">Zurück</button>
    </div>
    <ul v-else class="table-list">
      <li v-for="t in tables" :key="t.table_number">
        <button type="button" class="table-row" @click="openTable(t.table_number)">
          <span class="num">Tisch {{ t.table_number }}</span>
          <span class="meta muted">{{ t.order_count }} Bestellung(en) · {{ formatAmount(t.total_cents) }}</span>
        </button>
      </li>
    </ul>

    <button type="button" class="btn" style="width: 100%; margin-top: 1rem" @click="router.push({ name: 'hub' })">
      Zurück
    </button>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import * as store from '../store'
import { api } from '../api'
import { formatAmount } from '../utils/money'

const router = useRouter()
const loading = ref(true)
const tables = ref([])
const event = computed(() => store.selectedEvent.value)

onMounted(load)

async function load() {
  loading.value = true
  const ev = event.value
  if (!ev) {
    router.replace({ name: 'hub' })
    return
  }
  try {
    const r = await api(`/v1/tables/open?event_id=${ev.id}`)
    tables.value = r.tables || []
  } catch (e) {
    store.showToast(e.message || 'Laden fehlgeschlagen', 'err')
    tables.value = []
  } finally {
    loading.value = false
  }
}

function openTable(n) {
  store.activeTableNumber.value = n
  router.push({ name: 'pay-table', query: { table: String(n) } })
}
</script>

<style scoped>
.table-list {
  list-style: none;
  padding: 0;
  margin: 1rem 0 0;
}
.table-list li {
  margin-bottom: 0.5rem;
}
.table-row {
  width: 100%;
  text-align: left;
  padding: 0.85rem 1rem;
  border-radius: 0.75rem;
  border: 1px solid var(--border);
  background: var(--card);
  color: var(--text);
  cursor: pointer;
  min-height: 56px;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.num {
  font-weight: 600;
  font-size: 1.1rem;
}
</style>
