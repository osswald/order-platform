<template>
  <div v-if="showCard" class="section-card onboarding-card">
    <div class="onboarding-header">
      <div>
        <h2>{{ t('dashboard.onboarding.title') }}</h2>
        <p class="muted small">{{ t('dashboard.onboarding.subtitle', progress) }}</p>
      </div>
      <v-btn
        type="button"
        size="small"
        :disabled="acting"
        @click="dismissAll"
      >
        {{ t('dashboard.onboarding.dismissAll') }}
      </v-btn>
    </div>

    <div v-for="group in groupedTasks" :key="group.id" class="onboarding-group">
      <h3 class="onboarding-group-title">{{ group.title }}</h3>
      <div class="onboarding-list">
        <div
          v-for="task in group.tasks"
          :key="task.id"
          class="onboarding-item"
          :class="{ 'onboarding-item--done': task.done }"
        >
          <RouterLink
            v-if="taskRoute(task)"
            :to="taskRoute(task)!"
            class="onboarding-item-main"
          >
            <v-icon
              :icon="task.done ? 'mdi-check-circle' : 'mdi-circle-outline'"
              size="small"
              :class="task.done ? 'onboarding-icon--done' : 'onboarding-icon--open'"
            />
            <span class="onboarding-item-label">{{ taskLabel(task.id) }}</span>
            <v-icon
              v-if="!task.done"
              icon="mdi-chevron-right"
              size="small"
              class="onboarding-item-chevron"
            />
          </RouterLink>
          <div v-else class="onboarding-item-main">
            <v-icon
              :icon="task.done ? 'mdi-check-circle' : 'mdi-circle-outline'"
              size="small"
              :class="task.done ? 'onboarding-icon--done' : 'onboarding-icon--open'"
            />
            <span class="onboarding-item-label">{{ taskLabel(task.id) }}</span>
          </div>

          <div class="onboarding-item-actions">
            <v-btn
              v-if="!task.done"
              icon="mdi-check"
              size="x-small"
              :title="t('dashboard.onboarding.markDone')"
              :disabled="actingTaskId === task.id"
              @click="completeTask(task.id)"
            />
            <v-btn
              icon="mdi-close"
              size="x-small"
              :title="t('dashboard.onboarding.dismissTask')"
              :disabled="actingTaskId === task.id"
              @click="dismissTask(task.id)"
            />
          </div>
        </div>
      </div>
    </div>

    <p v-if="actionError" class="error">{{ actionError }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import { apiFetch } from '@/api'
import type { DashboardOnboarding, OnboardingTask } from '@/types/ui'
import {
  onboardingProgress,
  onboardingTaskRoute,
  visibleOnboardingTasks,
} from '@/utils/onboardingNavigation'

const props = defineProps<{
  organisationId: number
  onboarding: DashboardOnboarding
  canAccessOrganisationSettings?: boolean
}>()

const emit = defineEmits<{
  dismissed: []
  updated: []
}>()

const { t } = useI18n()
const acting = ref(false)
const actingTaskId = ref<string | null>(null)
const actionError = ref('')

const visibleTasks = computed(() =>
  visibleOnboardingTasks(props.onboarding.tasks, !!props.canAccessOrganisationSettings),
)

const progress = computed(() => onboardingProgress(visibleTasks.value))

const showCard = computed(() => {
  if (props.onboarding.dismissed) return false
  if (!visibleTasks.value.length) return false
  return visibleTasks.value.some((task) => !task.done)
})

const groupOrder = ['organisation', 'catalogue', 'event'] as const

const groupedTasks = computed(() => {
  const titles: Record<string, string> = {
    organisation: t('dashboard.onboarding.groupOrganisation'),
    catalogue: t('dashboard.onboarding.groupCatalogue'),
    event: t('dashboard.onboarding.groupEvent'),
  }
  return groupOrder
    .map((id) => ({
      id,
      title: titles[id],
      tasks: visibleTasks.value.filter((task) => task.group === id),
    }))
    .filter((group) => group.tasks.length > 0)
})

function taskLabel(taskId: string): string {
  const key = `dashboard.onboarding.tasks.${taskId}`
  const translated = t(key)
  return translated === key ? taskId : translated
}

function taskRoute(task: OnboardingTask) {
  return onboardingTaskRoute(task)
}

async function postTaskAction(taskId: string, action: 'complete' | 'dismiss') {
  actingTaskId.value = taskId
  actionError.value = ''
  try {
    const res = await apiFetch(
      `/organisations/${props.organisationId}/onboarding/tasks/${taskId}/${action}`,
      { method: 'POST' },
    )
    if (!res.ok) {
      const text = await res.text()
      throw new Error(text || res.statusText)
    }
    emit('updated')
  } catch (e: unknown) {
    actionError.value = e instanceof Error ? e.message : t('dashboard.onboarding.actionFailed')
  } finally {
    actingTaskId.value = null
  }
}

function completeTask(taskId: string) {
  return postTaskAction(taskId, 'complete')
}

function dismissTask(taskId: string) {
  return postTaskAction(taskId, 'dismiss')
}

async function dismissAll() {
  if (acting.value) return
  acting.value = true
  actionError.value = ''
  try {
    const res = await apiFetch(`/organisations/${props.organisationId}/onboarding/dismiss`, {
      method: 'POST',
    })
    if (!res.ok) {
      const text = await res.text()
      throw new Error(text || res.statusText)
    }
    emit('dismissed')
  } catch (e: unknown) {
    actionError.value = e instanceof Error ? e.message : t('dashboard.onboarding.dismissFailed')
  } finally {
    acting.value = false
  }
}
</script>

<style scoped>
.onboarding-card {
  margin-bottom: 1rem;
}

.onboarding-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1rem;
}

.onboarding-header h2 {
  margin: 0 0 0.25rem;
}

.onboarding-group + .onboarding-group {
  margin-top: 1rem;
}

.onboarding-group-title {
  margin: 0 0 0.5rem;
  font-size: 0.95rem;
  font-weight: 600;
}

.onboarding-list {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.onboarding-item {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.35rem 0.25rem 0.65rem;
  border-radius: 8px;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.onboarding-item--done {
  opacity: 0.72;
}

.onboarding-item-main {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex: 1;
  min-width: 0;
  padding: 0.25rem 0;
  text-decoration: none;
  color: inherit;
}

.onboarding-item-main:hover {
  color: inherit;
}

a.onboarding-item-main:hover {
  background: rgba(var(--v-theme-on-surface), 0.04);
  border-radius: 6px;
}

.onboarding-item-label {
  flex: 1;
}

.onboarding-item--done .onboarding-item-label {
  text-decoration: line-through;
}

.onboarding-icon--done {
  color: rgb(var(--v-theme-success));
}

.onboarding-icon--open {
  color: rgba(var(--v-theme-on-surface), 0.45);
}

.onboarding-item-chevron {
  opacity: 0.5;
}

.onboarding-item-actions {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}
</style>
