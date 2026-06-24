<template>
  <v-card class="hosted-pi-card" variant="outlined">
    <v-card-title>{{ t('hostedPi.title') }}</v-card-title>
    <v-card-text>
      <p class="hosted-pi-desc">
        {{ t('hostedPi.description') }}
      </p>

      <p v-if="error" class="hosted-pi-error">{{ error }}</p>

      <div v-if="loading && !instance && !showStartingMessage" class="hosted-pi-status">
        <v-progress-circular indeterminate size="20" width="2" />
        <span>{{ t('common.loading') }}</span>
      </div>

      <div v-else-if="showStartingMessage" class="hosted-pi-starting">
        <v-progress-circular indeterminate size="24" width="2" />
        <div>
          <p class="hosted-pi-starting-title">{{ t('hostedPi.startingTitle') }}</p>
          <p class="hosted-pi-starting-hint">
            {{ t('hostedPi.startingHint') }}
          </p>
        </div>
      </div>

      <template v-else-if="isActive">
        <p class="hosted-pi-status">
          <v-chip color="success" size="small" variant="tonal">{{ statusLabel }}</v-chip>
          <span v-if="expiresLabel" class="hosted-pi-expiry"> · {{ expiresLabel }}</span>
        </p>
        <div class="hosted-pi-actions">
          <v-btn
            v-if="instance?.url && instance?.status === 'running'"
            color="primary"
            variant="flat"
            type="button"
            @click="openInstance"
          >
            {{ t('hostedPi.open') }}
          </v-btn>
          <v-btn variant="outlined" type="button" :disabled="loading" @click="onStop">
            {{ t('hostedPi.stop') }}
          </v-btn>
        </div>
      </template>

      <template v-else-if="instance?.status === 'failed'">
        <p class="hosted-pi-error">{{ instance.last_error || t('hostedPi.startFailed') }}</p>
        <v-btn color="primary" variant="flat" type="button" :disabled="loading" @click="onStart">
          {{ t('hostedPi.restart') }}
        </v-btn>
      </template>

      <template v-else>
        <v-btn color="primary" variant="flat" type="button" :disabled="loading" @click="onStart">
          {{ t('hostedPi.start') }}
        </v-btn>
      </template>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { computed, onMounted, onUnmounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useHostedPi } from '../composables/useHostedPi'

const { t } = useI18n()

const props = defineProps({
  eventId: { type: Number, required: true },
})

const { instance, loading, starting, error, load, start, stop } = useHostedPi(
  computed(() => props.eventId),
)

const activeStatuses = new Set(['provisioning', 'running', 'stopping'])

const isActive = computed(() => activeStatuses.has(instance.value?.status))

const showStartingMessage = computed(
  () => starting.value || instance.value?.status === 'provisioning',
)

const statusLabel = computed(() => {
  const status = instance.value?.status
  if (status === 'provisioning') return t('hostedPi.status.provisioning')
  if (status === 'running') return t('hostedPi.status.running')
  if (status === 'stopping') return t('hostedPi.status.stopping')
  return status || t('hostedPi.status.unknown')
})

const expiresLabel = computed(() => {
  const expires = instance.value?.expires_at
  if (!expires) return ''
  const diffMs = new Date(expires).getTime() - Date.now()
  if (diffMs <= 0) return t('hostedPi.expires.expired')
  const hours = Math.floor(diffMs / (60 * 60 * 1000))
  const minutes = Math.floor((diffMs % (60 * 60 * 1000)) / (60 * 1000))
  if (hours > 0) return t('hostedPi.expires.remaining', { hours, minutes })
  return t('hostedPi.expires.remainingMinutes', { minutes })
})

let pollTimer = null

function startPolling() {
  stopPolling()
  pollTimer = setInterval(() => {
    if (isActive.value || instance.value?.status === 'provisioning') {
      load({ silent: true })
    }
  }, 5000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

async function onStart() {
  await start()
  startPolling()
}

async function onStop() {
  await stop()
  stopPolling()
}

function openInstance() {
  if (instance.value?.url) {
    window.open(instance.value.url, '_blank', 'noopener,noreferrer')
  }
}

watch(
  () => props.eventId,
  () => {
    load().then(() => {
      if (isActive.value) startPolling()
    })
  },
)

onMounted(async () => {
  await load()
  if (isActive.value) startPolling()
})

onUnmounted(stopPolling)
</script>

<style scoped>
.hosted-pi-card {
  margin-bottom: 1rem;
}
.hosted-pi-desc {
  margin: 0 0 1rem;
  color: rgba(var(--v-theme-on-surface), 0.7);
}
.hosted-pi-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1rem;
}
.hosted-pi-expiry {
  color: rgba(var(--v-theme-on-surface), 0.7);
  font-size: 0.9rem;
}
.hosted-pi-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}
.hosted-pi-error {
  color: rgb(var(--v-theme-error));
  margin-bottom: 0.75rem;
}
.hosted-pi-starting {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  margin-bottom: 1rem;
  padding: 0.75rem;
  border-radius: 0.5rem;
  background: rgba(var(--v-theme-primary), 0.08);
}
.hosted-pi-starting-title {
  margin: 0 0 0.25rem;
  font-weight: 600;
}
.hosted-pi-starting-hint {
  margin: 0;
  color: rgba(var(--v-theme-on-surface), 0.7);
  font-size: 0.9rem;
  line-height: 1.4;
}
</style>
