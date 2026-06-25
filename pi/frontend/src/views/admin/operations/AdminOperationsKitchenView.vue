<template>
  <div>
    <h1>Küchenmonitor</h1>
    <p class="muted">URLs für Küchenmonitore pro Station.</p>

    <div v-if="!kitchenMonitorRows.length" class="card">
      <p class="muted">Für dieses Event ist kein Küchenmonitor aktiviert.</p>
    </div>

    <div v-else class="card">
      <div
        v-for="row in kitchenMonitorRows"
        :key="row.printerId"
        class="kitchen-monitor-row"
      >
        <strong>{{ row.label }}</strong>
        <code class="display-url">{{ row.url }}</code>
        <div class="row">
          <button type="button" class="btn" @click="copyKitchenUrl(row.url)">URL kopieren</button>
          <button type="button" class="btn" @click="openKitchen(row.slug)">Monitor öffnen</button>
        </div>
      </div>
    </div>

    <button type="button" class="btn" style="width: 100%; margin-top: 1.5rem" @click="goBack">Zurück</button>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAdminOperations } from '@/composables/useAdminOperations'

const router = useRouter()
const { kitchenMonitorRows, copyKitchenUrl, openKitchen } = useAdminOperations()

function goBack() {
  router.push({ name: 'admin-operations' })
}
</script>

<style scoped>
.display-url {
  display: block;
  word-break: break-all;
  font-size: 0.8rem;
  margin: 0.35rem 0 0.75rem;
}
.kitchen-monitor-row {
  margin-bottom: 1rem;
}
.kitchen-monitor-row:last-child {
  margin-bottom: 0;
}
.kitchen-monitor-row strong {
  display: block;
}
</style>
