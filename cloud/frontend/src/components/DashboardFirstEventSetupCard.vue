<template>
  <div v-if="showCard" class="section-card first-event-setup-card">
    <div class="first-event-setup-header">
      <div>
        <h2>{{ t('dashboard.firstEventSetup.title') }}</h2>
        <p class="muted small">{{ t('dashboard.firstEventSetup.subtitle') }}</p>
      </div>
      <v-btn type="button" size="small" :disabled="acting" @click="dismiss">
        {{ t('dashboard.firstEventSetup.dismiss') }}
      </v-btn>
    </div>
    <div class="first-event-setup-actions">
      <v-btn color="primary" type="button" :disabled="acting" @click="startOrContinue">
        {{ continueMode ? t('dashboard.firstEventSetup.continue') : t('dashboard.firstEventSetup.start') }}
      </v-btn>
      <RouterLink :to="{ name: 'events-new' }" class="muted small">
        {{ t('dashboard.firstEventSetup.classicCreate') }}
      </RouterLink>
    </div>
    <p v-if="actionError" class="error">{{ actionError }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, useRouter } from 'vue-router'
import { apiJson } from '@/api'
import type { FirstEventSetupState } from '@/utils/firstEventSetup'
import {
  firstEventSetupCtaVisible,
  firstEventSetupIsContinue,
  firstEventSetupWizardRoute,
} from '@/utils/firstEventSetup'

const props = defineProps<{
  organisationId: number
  firstEventSetup: FirstEventSetupState
}>()

const emit = defineEmits<{
  dismissed: []
  updated: []
}>()

const { t } = useI18n()
const router = useRouter()
const acting = ref(false)
const actionError = ref('')

const showCard = computed(() => firstEventSetupCtaVisible(props.firstEventSetup))
const continueMode = computed(() => firstEventSetupIsContinue(props.firstEventSetup))

function startOrContinue() {
  router.push(firstEventSetupWizardRoute(props.organisationId))
}

async function dismiss() {
  acting.value = true
  actionError.value = ''
  try {
    await apiJson(`/organisations/${props.organisationId}/first-event-setup/dismiss`, {
      method: 'POST',
    })
    emit('dismissed')
  } catch {
    actionError.value = t('dashboard.firstEventSetup.dismissFailed')
  } finally {
    acting.value = false
  }
}
</script>

<style scoped>
.first-event-setup-card {
  margin-bottom: 1.25rem;
}
.first-event-setup-header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: flex-start;
  margin-bottom: 0.75rem;
}
.first-event-setup-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem 1.25rem;
  align-items: center;
}
</style>
