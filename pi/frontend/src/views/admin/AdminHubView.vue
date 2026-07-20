<template>
  <div>
    <h1>Admin</h1>
    <p class="muted">Konfiguration, Sync und Betrieb.</p>
    <p v-if="eventCount" class="muted small">{{ eventCount }} Event(s) im Bundle.</p>

    <div class="admin-topic-grid">
      <AdminTopicButton label="Synchronisation" :to="{ name: 'admin-sync' }">
        <template #icon>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
            <path d="M3 3v5h5" />
            <path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16" />
            <path d="M16 21h5v-5" />
          </svg>
        </template>
      </AdminTopicButton>

      <AdminTopicButton label="Betrieb" :to="{ name: 'admin-operations' }">
        <template #icon>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="2" y="3" width="20" height="14" rx="2" />
            <path d="M8 21h8" />
            <path d="M12 17v4" />
          </svg>
        </template>
      </AdminTopicButton>

      <AdminTopicButton
        v-if="androidApp"
        label="Bluetooth Drucker"
        :to="{ name: 'android-printer' }"
      >
        <template #icon>
          <svg viewBox="0 0 24 24" fill="currentColor">
            <path
              d="M17.71 7.71L12 2h-1v7.59L6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 11 14.41V22h1l5.71-5.71-4.3-4.29 4.3-4.29zM13 5.83l1.88 1.88L13 9.59V5.83zm1.88 10.46L13 18.17v-3.76l1.88 1.88z"
            />
          </svg>
        </template>
      </AdminTopicButton>

      <AdminTopicButton
        v-if="showUnpair"
        label="Gerät entkoppeln"
        :to="{ name: 'admin-unpair' }"
      >
        <template #icon>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
            <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
            <line x1="4" y1="4" x2="20" y2="20" />
          </svg>
        </template>
      </AdminTopicButton>
    </div>

    <button type="button" class="btn" style="width: 100%; margin-top: 1.5rem" @click="endAdmin">
      Admin beenden
    </button>

    <p class="muted small version-line">App {{ frontendLabel }}</p>
    <p class="muted small version-line">Pi {{ backendLabel ?? '—' }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api, isAndroidApp } from '@/api'
import AdminTopicButton from '@/components/AdminTopicButton.vue'
import { useAdminSession } from '@/composables/useAdminSession'
import { useAppVersion } from '@/composables/useAppVersion'
import { useBundle } from '@/composables/useBundle'
import type { SetupStatusResponse } from '@/types/api'

type HealthResponse = {
  status: string
  version: string
  build_time?: string | null
}

const { label: frontendLabel } = useAppVersion()
const backendLabel = ref<string | null>(null)
const router = useRouter()
const { clearAdminSession } = useAdminSession()
const { bundle } = useBundle()
const setupStatus = ref<SetupStatusResponse | null>(null)
const androidApp = computed(() => isAndroidApp())
const eventCount = computed(() => bundle.value?.events?.length || 0)
const showUnpair = computed(
  () => Boolean(setupStatus.value?.configured && setupStatus.value?.can_unpair),
)

onMounted(async () => {
  try {
    setupStatus.value = await api<SetupStatusResponse>('/v1/setup/status')
  } catch {
    /* Pi unreachable */
  }
  try {
    const health = await api<HealthResponse>('/health')
    const base = `v${health.version}`
    backendLabel.value =
      health.build_time && health.build_time !== 'dev' ? `${base} (${health.build_time})` : base
  } catch {
    backendLabel.value = null
  }
})

function endAdmin() {
  clearAdminSession()
  router.replace({ name: 'events' })
}
</script>

<style scoped>
.small {
  font-size: 0.8rem;
}
.admin-topic-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.75rem;
  margin-top: 1rem;
}
.version-line {
  margin: 1.5rem 0 0;
  text-align: center;
}
</style>
