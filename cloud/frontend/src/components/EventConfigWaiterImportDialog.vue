<template>
  <v-dialog :model-value="modelValue" max-width="32rem" @update:model-value="onVisibleChange">
    <v-card>
      <v-card-title>{{ $t('events.config.importWaiter') }}</v-card-title>
      <v-card-text>
        <p v-if="catalogLoading" class="muted">{{ $t('events.config.catalogLoading') }}</p>
        <p v-else-if="catalogError" class="error">{{ catalogError }}</p>
        <div class="form-field">
          <label>{{ $t('events.config.waiter') }}</label>
          <v-select
            v-model="pickedWaiterIds"
            :items="waiterOptions"
            item-title="label"
            item-value="value"
            :placeholder="$t('events.config.selectWaiters')"
            :loading="catalogLoading"
            :disabled="catalogLoading"
            multiple
            chips
            closable-chips
            density="compact"
            hide-details
          />
        </div>
      </v-card-text>
      <v-card-actions class="dialog-actions">
        <v-spacer />
        <v-btn variant="outlined" type="button" @click="cancel">{{ $t('common.cancel') }}</v-btn>
        <v-btn
          color="primary"
          type="button"
          :disabled="!pickedWaiterIds.length"
          @click="confirm"
        >
          {{ $t('events.config.apply') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
  catalogLoading: {
    type: Boolean,
    default: false,
  },
  catalogError: {
    type: String,
    default: '',
  },
  waiterOptions: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['update:modelValue', 'confirm', 'cancel'])

const pickedWaiterIds = defineModel('pickedWaiterIds', { type: Array, default: () => [] })

function onVisibleChange(value) {
  emit('update:modelValue', value)
  if (!value) {
    pickedWaiterIds.value = []
  }
}

function cancel() {
  emit('cancel')
  emit('update:modelValue', false)
  pickedWaiterIds.value = []
}

function confirm() {
  emit('confirm', [...pickedWaiterIds.value])
}
</script>

<style scoped>
.dialog-actions {
  padding: 0.75rem 1rem 1rem;
}
</style>
