<template>
  <div class="event-config-waiters-section">
    <div class="section-toolbar">
      <v-btn color="primary" type="button" @click="addWaiterRow">{{ $t('events.config.addWaiter') }}</v-btn>
      <v-btn variant="outlined" type="button" :disabled="catalogLoading" @click="$emit('import-from-org')">
        {{ $t('events.config.importFromOrg') }}
      </v-btn>
    </div>
    <VqDataTable
      :items="waiters"
      item-value="_key"
      :headers="waiterHeaders"
      class="vq-data-table nested"
      hide-default-footer
    >
      <template #item.name="{ index }">
        <v-text-field
          v-model="waiters[index].name"
          density="compact"
          hide-details="auto"
          required
          :rules="[rules.required]"
        />
      </template>
      <template #item.pin="{ index }">
        <v-text-field
          v-model="waiters[index].pin"
          density="compact"
          hide-details="auto"
          required
          :rules="[rules.required]"
        />
      </template>
      <template v-if="accountsEnabled" #item.subsidiary_code="{ index }">
        <v-text-field
          v-model="waiters[index].subsidiary_code"
          density="compact"
          hide-details="auto"
          maxlength="32"
        />
      </template>
      <template #item.actions="{ index }">
        <v-btn
          icon="mdi-delete"
          variant="text"
          color="error"
          type="button"
          @click="removeWaiterByIndex(index)"
        />
      </template>
    </VqDataTable>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import VqDataTable from './VqDataTable.vue'
import { rules } from '../utils/formRules.js'

const props = defineProps({
  catalogLoading: {
    type: Boolean,
    default: false,
  },
  accountsEnabled: {
    type: Boolean,
    default: false,
  },
})

defineEmits(['import-from-org'])

const waiters = defineModel({ type: Array, required: true })

const { t } = useI18n()

const waiterHeaders = computed(() => {
  const headers = [
    { title: t('events.config.waiterNameHeader'), key: 'name', sortable: false },
    { title: t('events.config.waiterPinHeader'), key: 'pin', sortable: false },
  ]
  if (props.accountsEnabled) {
    headers.push({ title: t('events.config.subsidiaryCode'), key: 'subsidiary_code', sortable: false })
  }
  headers.push({ title: '', key: 'actions', sortable: false, align: 'end', width: '4rem' })
  return headers
})

let waiterKey = 0

function addWaiterRow() {
  waiterKey += 1
  waiters.value.push({
    _key: `nw-${waiterKey}`,
    name: '',
    pin: '0000',
    source_waiter_id: null,
    subsidiary_code: '',
  })
}

function removeWaiterByIndex(ix) {
  if (ix >= 0) waiters.value.splice(ix, 1)
}
</script>

<style scoped>
.vq-data-table.nested {
  border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
}
</style>
