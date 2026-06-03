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
      <button
        type="button"
        class="btn primary"
        :disabled="retryingId === job.id"
        @click="retry(job)"
      >
        Erneut drucken
      </button>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useEventContext } from '../composables/useEventContext'
import { useStationPrintFailures } from '../composables/useStationPrintFailures'

const { event, waiter, showToast, selectedEventId } = useEventContext()
const { failedJobs, loadingFailed, retryingId, loadFailedJobs, retryJob, failureLabel } =
  useStationPrintFailures()

async function refresh() {
  await loadFailedJobs({
    eventId: selectedEventId.value,
    waiterUuid: waiter.value?.uuid,
  })
}

async function retry(job) {
  await retryJob(job.id, {
    showToast,
    onFailed: (failed) => showToast(failureLabel(failed), 'err'),
  })
  await refresh()
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
.small {
  font-size: 0.85rem;
  word-break: break-word;
}
</style>
