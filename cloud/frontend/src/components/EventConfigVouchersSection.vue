<template>
  <div class="event-config-vouchers-section">
    <div class="section-toolbar">
      <v-btn color="primary" type="button" @click="addVoucher">{{ $t('events.config.addVoucher') }}</v-btn>
    </div>
    <p v-if="!vouchers.length" class="muted">{{ $t('events.config.noVouchers') }}</p>
    <div v-for="(vd, vi) in vouchers" :key="'vd-' + vi" class="config-card">
      <div class="config-card-header">
        <span>{{ vd.name || $t('events.config.unnamedVoucher') }}</span>
        <v-btn icon="mdi-delete" variant="text" color="error" type="button" @click="removeVoucher(vi)" />
      </div>
      <div class="form-field">
        <FormLabel required>{{ $t('events.config.name') }}</FormLabel>
        <v-text-field
          v-model="vd.name"
          :placeholder="$t('events.config.voucherPlaceholder')"
          density="compact"
          hide-details="auto"
          required
          :rules="[rules.required]"
        />
      </div>
      <div class="form-field">
        <label>{{ $t('events.config.kind') }}</label>
        <v-select
          v-model="vd.kind"
          :items="voucherKindOptions"
          item-title="label"
          item-value="value"
          density="compact"
          hide-details
        />
      </div>
      <div v-if="vd.kind === 'fixed_amount'" class="form-field">
        <label>{{ $t('events.config.amountWithCurrency', { currency: currencyLabel }) }}</label>
        <v-number-input
          v-model="vd.value_amount"
          :min="0.01"
          :max="9999"
          :step="0.01"
          control-variant="stacked"
          density="compact"
          hide-details
        />
      </div>
      <template v-else>
        <div class="form-field">
          <label>{{ $t('events.config.eligibleArticles') }}</label>
          <v-select
            v-model="vd.allowed_article_ids"
            :items="articleOptions"
            item-title="name"
            item-value="value"
            :placeholder="$t('events.config.selectArticles')"
            :loading="catalogLoading"
            :disabled="catalogLoading"
            multiple
            chips
            closable-chips
            density="compact"
            hide-details
          />
        </div>
        <v-checkbox
          v-model="vd.include_additions"
          :label="$t('events.config.includeAdditions')"
          hide-details
          density="compact"
        />
      </template>
    </div>
  </div>
</template>

<script setup>
import FormLabel from './FormLabel.vue'
import { rules } from '../utils/formRules.js'

defineProps({
  articleOptions: {
    type: Array,
    default: () => [],
  },
  catalogLoading: {
    type: Boolean,
    default: false,
  },
  currencyLabel: {
    type: String,
    default: 'EUR',
  },
  voucherKindOptions: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['voucher-removed'])
const vouchers = defineModel({ type: Array, required: true })

function newUuid() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) return crypto.randomUUID()
  return `local-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

function addVoucher() {
  vouchers.value.push({
    uuid: newUuid(),
    name: '',
    kind: 'fixed_amount',
    value_amount: 20,
    allowed_article_ids: [],
    include_additions: true,
  })
}

function removeVoucher(idx) {
  const removed = vouchers.value[idx]
  vouchers.value.splice(idx, 1)
  if (removed?.uuid) {
    emit('voucher-removed', removed.uuid)
  }
}
</script>
