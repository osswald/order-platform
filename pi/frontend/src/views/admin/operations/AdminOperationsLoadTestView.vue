<template>
  <div>
    <h1>Lasttest</h1>
    <p class="muted">
      Simuliert parallele Bestellungen (Kellner + Kassen) gegen das Event im Testbetrieb.
      Kassenschubladen werden mit angesteuert.
    </p>

    <div v-if="!isTestEvent" class="card">
      <p class="muted">Nur für Events im Status Testbetrieb verfügbar.</p>
    </div>

    <template v-else>
      <div class="card form-card">
        <label class="field">
          <span>Kellner</span>
          <input
            v-model.number="waiterCount"
            type="number"
            min="0"
            :max="maxWaiters"
            :disabled="running || actionBusy"
          />
          <span class="hint">von {{ maxWaiters }} verfügbar</span>
        </label>
        <label class="field">
          <span>Kassen</span>
          <input
            v-model.number="cashRegisterCount"
            type="number"
            min="0"
            :max="maxRegisters"
            :disabled="running || actionBusy"
          />
          <span class="hint">von {{ maxRegisters }} verfügbar</span>
        </label>
        <div class="field-row">
          <label class="field">
            <span>Tische von</span>
            <input
              v-model.number="tableMin"
              type="number"
              min="1"
              :disabled="running || actionBusy"
            />
          </label>
          <label class="field">
            <span>bis</span>
            <input
              v-model.number="tableMax"
              type="number"
              min="1"
              :disabled="running || actionBusy"
            />
          </label>
        </div>
        <label class="field">
          <span>Bestellungen gesamt</span>
          <input
            v-model.number="totalOrders"
            type="number"
            min="1"
            :disabled="running || actionBusy"
          />
        </label>
        <p class="muted small">
          ≈ {{ actorsPerBurst }} / Min · Dauer ≈ {{ estimatedMinutes }} Min
        </p>
        <div class="actions">
          <button
            type="button"
            class="btn primary"
            :disabled="busy || actionBusy || running || actorsPerBurst <= 0"
            @click="startLoadTest"
          >
            Starten
          </button>
          <button
            type="button"
            class="btn"
            :disabled="busy || actionBusy || !running"
            @click="stopLoadTest"
          >
            Stoppen
          </button>
        </div>
      </div>

      <div class="card">
        <p>
          Status: <strong>{{ statusLabel }}</strong>
        </p>
        <p class="muted small">
          {{ status.placed ?? 0 }} OK · {{ status.failed ?? 0 }} Fehler ·
          {{ status.receipts_printed ?? 0 }} Belege · Burst
          {{ status.current_burst ?? 0 }}/{{ status.total_bursts ?? 0 }}
        </p>
        <p v-if="status.last_error" class="err small">{{ status.last_error }}</p>
      </div>
    </template>

    <button type="button" class="btn" style="width: 100%; margin-top: 1.5rem" @click="goBack">
      Zurück
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useLoadTest } from '@/composables/useLoadTest'

const router = useRouter()
const {
  busy,
  actionBusy,
  status,
  running,
  isTestEvent,
  maxWaiters,
  maxRegisters,
  waiterCount,
  cashRegisterCount,
  tableMin,
  tableMax,
  totalOrders,
  actorsPerBurst,
  estimatedMinutes,
  startLoadTest,
  stopLoadTest,
} = useLoadTest()

const statusLabel = computed(() => {
  const map: Record<string, string> = {
    idle: 'Bereit',
    running: 'Läuft',
    stopping: 'Stoppt…',
    done: 'Fertig',
    failed: 'Fehler',
  }
  return map[status.value.state] || status.value.state
})

function goBack() {
  router.push({ name: 'admin-operations' })
}
</script>

<style scoped>
.form-card {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: 0.9rem;
}
.field input {
  padding: 0.5rem 0.65rem;
  border-radius: 8px;
  border: 1px solid var(--border, #ccc);
  font-size: 1rem;
}
.field-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
}
.hint {
  font-size: 0.75rem;
  color: var(--muted, #666);
}
.small {
  font-size: 0.8rem;
  margin: 0;
}
.actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.5rem;
  margin-top: 0.25rem;
}
.err {
  color: var(--danger, #b91c1c);
}
</style>
