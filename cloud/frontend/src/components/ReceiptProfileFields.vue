<template>
  <div class="receipt-profile-fields">
    <v-checkbox
      v-model="model.logo_enabled"
      :label="$t('receipts.printLogo')"
      hide-details
      density="compact"
    />
    <v-checkbox
      v-model="model.show_event_title"
      :label="$t('receipts.showEventTitle')"
      hide-details
      density="compact"
    />
    <v-checkbox
      v-if="showPriceOption"
      v-model="model.show_price"
      :label="$t('receipts.showPrices')"
      hide-details
      density="compact"
    />
    <div class="form-field">
      <label>{{ $t('receipts.fontSizeLabel', { field: resolvedPickupLabel }) }}</label>
      <v-select
        v-model="model.size_table_or_pickup"
        :items="tableSizeOptions"
        item-title="label"
        item-value="value"
        density="compact"
        hide-details
      />
    </div>
    <div class="form-field">
      <label>{{ $t('receipts.orderLinesFontSize') }}</label>
      <v-select
        v-model="model.size_order_lines"
        :items="lineSizeOptions"
        item-title="label"
        item-value="value"
        density="compact"
        hide-details
      />
    </div>
    <div class="form-field">
      <label>{{ $t('receipts.footerLabel') }}</label>
      <v-textarea
        v-model="model.bottom_line"
        rows="3"
        auto-grow
        :placeholder="$t('receipts.optionalPlaceholder')"
        density="compact"
        hide-details
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const model = defineModel({ type: Object, required: true })

const props = defineProps({
  pickupLabel: { type: String, default: '' },
  /** Kitchen station slips never print prices; only shown for customer pickup profile. */
  showPriceOption: { type: Boolean, default: true },
})

const resolvedPickupLabel = computed(() => props.pickupLabel || t('receipts.tablePickup'))

const tableSizeOptions = computed(() => [
  { label: t('receipts.sizeNormal'), value: 'normal' },
  { label: t('receipts.sizeLarge'), value: 'large' },
  { label: t('receipts.sizeXLarge'), value: 'xlarge' },
])

const lineSizeOptions = computed(() => [
  { label: t('receipts.sizeNormal'), value: 'normal' },
  { label: t('receipts.sizeLarge'), value: 'large' },
])
</script>

<style scoped>
.receipt-profile-fields {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding-top: 0.5rem;
}
</style>
