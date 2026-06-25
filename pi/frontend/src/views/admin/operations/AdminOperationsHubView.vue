<template>
  <div>
    <h1>Betrieb</h1>
    <p class="muted">Testdruck, Pickup Screen und Display-URLs.</p>

    <div v-if="!bundle || !events.length" class="card">
      <p class="muted">Keine Events im Bundle. Zuerst Konfiguration laden.</p>
    </div>

    <div v-else class="admin-topic-grid">
      <AdminTopicButton label="Testdruck" :to="{ name: 'admin-operations-test-print' }">
        <template #icon>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="6 9 6 2 18 2 18 9" />
            <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2" />
            <rect x="6" y="14" width="12" height="8" />
          </svg>
        </template>
      </AdminTopicButton>

      <AdminTopicButton
        v-if="hasKitchenMonitor"
        label="Küchenmonitor"
        :to="{ name: 'admin-operations-kitchen' }"
      >
        <template #icon>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="2" y="3" width="20" height="14" rx="2" />
            <path d="M8 21h8" />
            <path d="M12 17v4" />
          </svg>
        </template>
      </AdminTopicButton>

      <AdminTopicButton
        v-if="hasCashRegisters"
        label="Pickup Screen"
        :to="{ name: 'admin-operations-pickup' }"
      >
        <template #icon>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M4 10h16" />
            <path d="M6 6h12v12H6z" />
            <path d="M9 14h6" />
          </svg>
        </template>
      </AdminTopicButton>

      <AdminTopicButton
        v-if="hasCashRegisters"
        label="Kundendisplay"
        :to="{ name: 'admin-operations-display' }"
      >
        <template #icon>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="2" y="4" width="20" height="14" rx="2" />
            <path d="M8 22h8" />
            <path d="M12 18v4" />
          </svg>
        </template>
      </AdminTopicButton>
    </div>

    <button type="button" class="btn" style="width: 100%; margin-top: 1.5rem" @click="goBack">Zurück</button>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import AdminTopicButton from '@/components/AdminTopicButton.vue'
import { useAdminOperations } from '@/composables/useAdminOperations'

const router = useRouter()
const { bundle, events, hasKitchenMonitor, hasCashRegisters } = useAdminOperations()

function goBack() {
  router.push({ name: 'admin' })
}
</script>

<style scoped>
.admin-topic-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.75rem;
  margin-top: 1rem;
}
</style>
