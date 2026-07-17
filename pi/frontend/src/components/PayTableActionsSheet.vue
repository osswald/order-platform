<template>
  <Teleport to="body">
    <div v-if="open" class="sheet-backdrop" @click.self="close" />
    <div v-if="open" class="sheet" role="dialog" aria-modal="true">
      <header class="sheet-header">
        <h3>{{ stepTitle }}</h3>
        <button v-if="step !== 'menu'" type="button" class="link-back" @click="step = 'menu'">← Zurück</button>
      </header>

      <template v-if="step === 'menu'">
        <div class="menu-actions">
          <button type="button" class="btn menu-btn" @click="$emit('redeem-voucher')">Gutschein einlösen</button>
          <template v-if="!voucherOnly && !isInstantMode">
            <button v-if="!hideTransfer" type="button" class="btn menu-btn" @click="step = 'transfer'">
              Tisch umbuchen
            </button>
            <button type="button" class="btn menu-btn" @click="openCollective">Sammelrechnung</button>
          </template>
          <template v-else-if="!voucherOnly">
            <button v-if="!hideTransfer" type="button" class="btn menu-btn" @click="step = 'transfer'">
              Tisch umbuchen
            </button>
          </template>
        </div>
        <button type="button" class="btn" @click="close">Abbrechen</button>
      </template>

      <template v-else-if="step === 'transfer'">
        <TableKeypad hint="Ziel-Tischnummer" @submit="onTransferSubmit" />
      </template>

      <template v-else-if="step === 'collective'">
        <p v-if="loadingBills" class="muted">Laden…</p>
        <p v-else-if="!bills.length" class="muted collective-hint">
          Leere Sammelrechnungen erscheinen hier nach Anlegen im Hub, oder unten neu erstellen.
        </p>
        <ul v-else class="bill-list">
          <li v-for="b in bills" :key="b.id">
            <button type="button" class="bill-row" @click="assignToBill(b)">
              <span class="name">{{ b.name }}</span>
              <span class="meta muted">{{ formatMoney(b.total_cents, currency) }}</span>
            </button>
          </li>
        </ul>
        <button type="button" class="btn primary" style="width: 100%; margin-top: 0.75rem" @click="step = 'new-name'">
          Neue Sammelrechnung
        </button>
        <button type="button" class="btn" style="width: 100%; margin-top: 0.5rem" @click="close">Abbrechen</button>
      </template>

      <template v-else-if="step === 'new-name'">
        <label class="field-label">Name</label>
        <input v-model="newName" type="text" class="text-input" maxlength="128" placeholder="z. B. Personal" />
        <button
          type="button"
          class="btn primary"
          style="width: 100%; margin-top: 1rem"
          :disabled="!newName.trim() || busy"
          @click="assignNewBill"
        >
          Erstellen und zuordnen
        </button>
      </template>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { api } from '@/api'
import { useEventContext } from '@/composables/useEventContext'
import type {
  AssignCollectiveResponse,
  CollectiveBillListItem,
  LineSelection,
  OpenCollectiveBillsResponse,
} from '@/types/api'
import { getErrorMessage } from '@/types/api'
import { formatMoney } from '@/utils/money'
import TableKeypad from './TableKeypad.vue'

const { showToast, event, currency } = useEventContext()

const isInstantMode = computed(
  () => (event.value?.payment_mode || 'pay_later').toLowerCase() === 'instant',
)

const props = withDefaults(
  defineProps<{
    open?: boolean
    eventId: number
    fromTable?: number | null
    selections?: LineSelection[]
    voucherOnly?: boolean
    /** Hide "Tisch umbuchen" (e.g. register orders have no source table). */
    hideTransfer?: boolean
    /** Assign-collective endpoint; defaults to the table-scoped route. */
    assignPath?: string | null
  }>(),
  {
    open: false,
    fromTable: null,
    selections: () => [],
    voucherOnly: false,
    hideTransfer: false,
    assignPath: null,
  },
)

const emit = defineEmits<{
  close: []
  done: []
  'redeem-voucher': []
}>()

const step = ref('menu')
const bills = ref<CollectiveBillListItem[]>([])
const loadingBills = ref(false)
const newName = ref('')
const busy = ref(false)

const stepTitle = computed(() => {
  if (step.value === 'transfer') return 'Tisch umbuchen'
  if (step.value === 'collective') return 'Sammelrechnung wählen'
  if (step.value === 'new-name') return 'Neue Sammelrechnung'
  return 'Aktionen'
})

watch(
  () => props.open,
  (v) => {
    if (v) {
      step.value = 'menu'
      newName.value = ''
      bills.value = []
    }
  },
)

function close() {
  emit('close')
}

async function openCollective() {
  step.value = 'collective'
  loadingBills.value = true
  try {
    const r = await api<OpenCollectiveBillsResponse>(`/v1/collective-bills/open?event_id=${props.eventId}`)
    bills.value = r.collective_bills || []
  } catch (e: unknown) {
    showToast(getErrorMessage(e, 'Laden fehlgeschlagen'), 'err')
    step.value = 'menu'
  } finally {
    loadingBills.value = false
  }
}

async function postAssign(body: { collective_bill_id?: number; new_name?: string }) {
  busy.value = true
  try {
    const path = props.assignPath || `/v1/tables/${props.fromTable}/assign-collective`
    const res = await api<Pick<AssignCollectiveResponse, 'name'>>(path, {
      method: 'POST',
      body: JSON.stringify({
        event_id: props.eventId,
        selections: props.selections,
        ...body,
      }),
    })
    showToast(`Posten zu «${res.name}» hinzugefügt`, 'ok')
    emit('done')
    close()
  } catch (e: unknown) {
    showToast(getErrorMessage(e, 'Zuordnung fehlgeschlagen'), 'err')
  } finally {
    busy.value = false
  }
}

function assignToBill(b: CollectiveBillListItem) {
  postAssign({ collective_bill_id: b.id })
}

function assignNewBill() {
  const name = newName.value.trim()
  if (!name) return
  postAssign({ new_name: name })
}

async function onTransferSubmit(targetTable: number) {
  if (targetTable === props.fromTable) {
    showToast('Ziel-Tisch muss ein anderer Tisch sein', 'err')
    return
  }
  busy.value = true
  try {
    await api(`/v1/tables/${props.fromTable}/transfer-lines`, {
      method: 'POST',
      body: JSON.stringify({
        event_id: props.eventId,
        target_table_number: targetTable,
        selections: props.selections,
      }),
    })
    showToast(`Posten nach Tisch ${targetTable} verschoben`, 'ok')
    emit('done')
    close()
  } catch (e: unknown) {
    showToast(getErrorMessage(e, 'Umbuchen fehlgeschlagen'), 'err')
  } finally {
    busy.value = false
  }
}
</script>

<style scoped>
.sheet-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  z-index: 150;
}
.sheet {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 151;
  background: var(--card);
  border-radius: 1rem 1rem 0 0;
  padding: 1rem 1rem calc(1rem + var(--safe-bottom));
  max-height: 85vh;
  overflow-y: auto;
}
.sheet-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}
.sheet-header h3 {
  margin: 0;
}
.link-back {
  border: none;
  background: none;
  color: var(--primary);
  font-size: 0.95rem;
  cursor: pointer;
}
.menu-actions {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 1rem;
}
.menu-btn {
  width: 100%;
  min-height: 52px;
  font-size: 1.05rem;
  font-weight: 600;
}
.bill-list {
  list-style: none;
  padding: 0;
  margin: 0;
  max-height: 40vh;
  overflow-y: auto;
}
.bill-row {
  width: 100%;
  text-align: left;
  padding: 0.75rem 1rem;
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  background: var(--bg);
  color: var(--text);
  margin-bottom: 0.5rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
}
.name {
  font-weight: 600;
}
.collective-hint {
  margin: 0 0 0.75rem;
  font-size: 0.9rem;
  line-height: 1.35;
}
.field-label {
  display: block;
  margin-bottom: 0.35rem;
  font-size: 0.9rem;
}
.text-input {
  width: 100%;
  padding: 0.65rem 0.75rem;
  border-radius: 0.5rem;
  border: 1px solid var(--border);
  font-size: 1rem;
}
</style>
