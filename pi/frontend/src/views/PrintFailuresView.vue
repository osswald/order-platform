<template>
  <div>
    <h1>Druckfehler</h1>
    <p class="muted">{{ event?.name }} · {{ waiter?.name }}</p>

    <div class="row">
      <button type="button" class="btn" :disabled="loadingFailed" @click="refresh">Aktualisieren</button>
      <RouterLink class="btn" :to="{ name: 'hub' }">Zurück</RouterLink>
    </div>

    <p v-if="loadingFailed" class="muted">Laden…</p>
    <p v-else-if="!failedJobs.length" class="muted">Keine fehlgeschlagenen Stationsbons.</p>

    <div v-for="job in failedJobs" :key="job.id" class="card receipt-card">
      <div>
        <strong>{{ job.station_name || job.station_uuid || 'Station' }}</strong>
        <p class="muted">
          <template v-if="job.table_number">Tisch {{ job.table_number }}</template>
          <template v-if="job.order_number">
            <template v-if="job.table_number"> · </template>
            Bestellung #{{ job.order_number }}
          </template>
        </p>
        <p v-if="job.last_error" class="err small">{{ job.last_error }}</p>
      </div>
      <div class="card-actions">
        <button
          type="button"
          class="btn primary"
          :disabled="retryingId === job.id || deletingId === job.id"
          @click="retry(job)"
        >
          Erneut drucken
        </button>
        <button
          type="button"
          class="btn"
          :disabled="retryingId === job.id || deletingId === job.id"
          @click="dismiss(job)"
        >
          Verwerfen
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useEventContext } from '@/composables/useEventContext'
import type { PrintJobSummary } from '@/types/api'
import { useStationPrintFailures } from '@/composables/useStationPrintFailures'

const { event, waiter, showToast, selectedEventId } = useEventContext()
const { failedJobs, loadingFailed, retryingId, deletingId, loadFailedJobs, retryJob, deleteJob, failureLabel } =
  useStationPrintFailures()

async function refresh() {
  const eventId = selectedEventId.value
  const waiterUuid = waiter.value?.uuid
  if (!eventId || !waiterUuid) return
  await loadFailedJobs({ eventId, waiterUuid })
}

async function retry(job: PrintJobSummary) {
  await retryJob(job.id, {
    showToast,
    onFailed: (failed) => showToast(failureLabel(failed), 'err'),
  })
  await refresh()
}

async function dismiss(job: PrintJobSummary) {
  const station = job.station_name || job.station_uuid || 'Station'
  const confirmed = window.confirm(
    `Druckauftrag für «${station}» verwerfen? Der Bon wird nicht gedruckt.`,
  )
  if (!confirmed) return
  await deleteJob(job.id, { showToast })
}

onMounted(refresh)
</script>

<style scoped>
.receipt-card {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-top: 0.75rem;
}
.card-actions {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  flex-shrink: 0;
}
.small {
  font-size: 0.85rem;
  word-break: break-word;
}
</style>
