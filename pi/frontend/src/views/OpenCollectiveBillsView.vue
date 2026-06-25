<template>
  <div>
    <h1>Sammelrechnungen</h1>
    <p class="muted">{{ event?.name }}</p>

    <button
      v-if="!isInstantMode"
      type="button"
      class="btn primary"
      style="width: 100%; margin-top: 0.75rem"
      :disabled="creating"
      @click="createBill"
    >
      Neue Sammelrechnung
    </button>

    <p v-if="loading" class="muted" style="margin-top: 1rem">Laden…</p>
    <div v-else-if="!bills.length" class="card" style="margin-top: 1rem">
      <p>Keine offenen Sammelrechnungen.</p>
    </div>
    <ul v-else class="table-list">
      <li v-for="b in bills" :key="b.id">
        <button type="button" class="table-row" @click="openBill(b.id)">
          <span class="num">{{ b.name }}</span>
          <span class="meta muted">
            <template v-if="b.order_count === 0">Noch keine Posten</template>
            <template v-else>{{ b.order_count }} Bestellung(en)</template>
            · {{ formatAmount(b.total_cents) }}
          </span>
        </button>
      </li>
    </ul>

    <button type="button" class="btn" style="width: 100%; margin-top: 1rem" @click="router.push({ name: 'hub' })">
      Zurück
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useEventContext } from '@/composables/useEventContext'
import { api } from '@/api'
import type {
  CollectiveBillCreatedResponse,
  CollectiveBillListItem,
  OpenCollectiveBillsResponse,
} from '@/types/api'
import { getErrorMessage } from '@/types/api'
import { formatAmount } from '@/utils/money'

const router = useRouter()
const loading = ref(true)
const creating = ref(false)
const bills = ref<CollectiveBillListItem[]>([])
const { event, showToast } = useEventContext()

const isInstantMode = computed(
  () => (event.value?.payment_mode || 'pay_later').toLowerCase() === 'instant',
)

onMounted(load)

async function load() {
  loading.value = true
  const ev = event.value
  if (!ev) {
    router.replace({ name: 'hub' })
    return
  }
  try {
    const r = await api<OpenCollectiveBillsResponse>(`/v1/collective-bills/open?event_id=${ev.id}`)
    bills.value = r.collective_bills || []
  } catch (e: unknown) {
    showToast(getErrorMessage(e, 'Laden fehlgeschlagen'), 'err')
    bills.value = []
  } finally {
    loading.value = false
  }
}

async function createBill() {
  const name = window.prompt('Name der Sammelrechnung', 'Personal')
  if (!name?.trim()) return
  const ev = event.value
  if (!ev) return
  creating.value = true
  try {
    const r = await api<CollectiveBillCreatedResponse>('/v1/collective-bills', {
      method: 'POST',
      body: JSON.stringify({ event_id: ev.id, name: name.trim() }),
    })
    showToast(`«${r.name}» erstellt`, 'ok')
    await load()
    if (r.id) {
      router.push({ name: 'pay-collective', query: { id: String(r.id) } })
    }
  } catch (e: unknown) {
    showToast(getErrorMessage(e, 'Erstellen fehlgeschlagen'), 'err')
  } finally {
    creating.value = false
  }
}

function openBill(id: number) {
  router.push({ name: 'pay-collective', query: { id: String(id) } })
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
