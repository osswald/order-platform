<template>
  <div class="event-status-stepper">
    <v-stepper :model-value="currentStep" flat :mobile="isMobile">
      <v-stepper-header>
        <template v-for="(step, index) in EVENT_STATUS_ORDER" :key="step">
          <v-stepper-item
            :value="index + 1"
            :title="statusLabel(step)"
            :color="eventStatusColor(step)"
            :icon="stepIcon(index)"
            :complete="index < currentIndex"
            :editable="isClickable(step)"
            :class="{ 'event-status-stepper__item--clickable': isClickable(step) }"
            @click="onStepClick(step)"
          />
          <v-divider v-if="index < EVENT_STATUS_ORDER.length - 1" />
        </template>
      </v-stepper-header>
    </v-stepper>

    <v-dialog v-model="dialogOpen" max-width="32rem">
      <v-card>
        <v-card-title>{{ t('events.statusConfirm.title') }}</v-card-title>
        <v-card-text>{{ confirmMessage }}</v-card-text>
        <v-card-actions class="dialog-actions">
          <v-spacer />
          <v-btn variant="outlined" type="button" @click="cancelTransition">
            {{ t('common.cancel') }}
          </v-btn>
          <v-btn color="primary" type="button" @click="confirmTransition">
            {{ t('events.statusConfirm.confirm') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useDisplay } from 'vuetify'
import { EVENT_STATUS_ORDER, eventStatusColor, eventStatusIndex } from '@/utils/eventStatus'
import { statusLabel } from '@/utils/dashboardMetrics'
import type { EventStatusKey } from '@/utils/eventStatus'
import type { SelectOption } from '@/types/ui'

const props = withDefaults(
  defineProps<{
    modelValue: string
    selectableStatusOptions: SelectOption<string>[]
    editMode?: boolean
  }>(),
  {
    editMode: false,
  },
)

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const { t } = useI18n()
const { mobile: isMobile } = useDisplay()

const dialogOpen = ref(false)
const pendingStatus = ref<EventStatusKey | null>(null)

const currentIndex = computed(() => eventStatusIndex(props.modelValue))

const currentStep = computed(() => {
  const index = currentIndex.value
  return index >= 0 ? index + 1 : 1
})

function stepIcon(index: number): string | undefined {
  return index < currentIndex.value ? undefined : 'mdi-circle'
}

const selectableValues = computed(() =>
  new Set(props.selectableStatusOptions.map((option) => option.value)),
)

const nextAllowedStatus = computed((): EventStatusKey | null => {
  const nextIndex = currentIndex.value + 1
  if (nextIndex < 0 || nextIndex >= EVENT_STATUS_ORDER.length) return null
  const next = EVENT_STATUS_ORDER[nextIndex]
  return selectableValues.value.has(next) ? next : null
})

const confirmMessage = computed(() => {
  const target = pendingStatus.value
  if (!target) return ''
  if (target === 'prod') return t('events.confirmProd')
  if (target === 'test') return t('events.statusConfirm.toTest')
  if (target === 'archive') return t('events.statusConfirm.toArchive')
  return ''
})

function isClickable(step: EventStatusKey): boolean {
  if (!props.editMode) return false
  return nextAllowedStatus.value === step
}

function onStepClick(step: EventStatusKey) {
  if (!isClickable(step)) return
  pendingStatus.value = step
  dialogOpen.value = true
}

function cancelTransition() {
  dialogOpen.value = false
  pendingStatus.value = null
}

function confirmTransition() {
  if (pendingStatus.value) {
    emit('update:modelValue', pendingStatus.value)
  }
  cancelTransition()
}
</script>

<style scoped>
.event-status-stepper {
  width: 100%;
}

.event-status-stepper :deep(.v-stepper-header) {
  box-shadow: none;
}

.event-status-stepper__item--clickable {
  cursor: pointer;
}

.dialog-actions {
  padding: 0.5rem 1rem 1rem;
}
</style>
