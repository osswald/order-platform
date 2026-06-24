<template>
  <div class="event-config-stations-section">
    <p v-if="catalogLoading" class="muted catalog-loading-hint">{{ $t('events.config.catalogLoading') }}</p>
    <p v-else-if="catalogError" class="error">{{ catalogError }}</p>
    <div class="section-toolbar">
      <v-btn color="primary" type="button" @click="addStation">{{ $t('events.config.addStation') }}</v-btn>
    </div>
    <div v-for="(st, idx) in stations" :key="'st-' + idx" class="config-card">
      <div class="config-card-header">
        <span>{{ st.name || $t('events.config.unnamedStation') }}</span>
        <v-btn
          icon="mdi-delete"
          variant="text"
          color="error"
          type="button"
          :aria-label="$t('events.config.remove')"
          @click="removeStation(idx)"
        />
      </div>
      <div class="form-field">
        <FormLabel required>{{ $t('events.config.name') }}</FormLabel>
        <v-text-field
          v-model="st.name"
          :placeholder="$t('events.config.stationNamePlaceholder')"
          density="compact"
          hide-details="auto"
          required
          :rules="[rules.required]"
        />
      </div>
      <div class="form-field">
        <label>{{ $t('events.config.printer') }}</label>
        <v-select
          v-model="st.printer_appliance_id"
          :items="printerOptions"
          item-title="name"
          item-value="id"
          :placeholder="$t('events.config.noPrinter')"
          clearable
          density="compact"
          hide-details
        />
      </div>
      <div v-if="alternativePrintersEnabled" class="printer-rules-block">
        <div class="printer-rules-header">
          <label>{{ $t('events.config.printerRules') }}</label>
          <v-btn size="small" variant="text" type="button" @click="addPrinterRule(idx)">
            {{ $t('events.config.addRule') }}
          </v-btn>
        </div>
        <div
          v-for="(rule, ruleIdx) in st.printer_rules"
          :key="'rule-' + idx + '-' + ruleIdx"
          class="printer-rule-card"
        >
          <div class="printer-rule-card-header">
            <span>{{ $t('events.config.ruleN', { n: ruleIdx + 1 }) }}</span>
            <v-btn
              icon="mdi-delete"
              variant="text"
              color="error"
              type="button"
              :aria-label="$t('events.config.removeRule')"
              @click="removePrinterRule(idx, ruleIdx)"
            />
          </div>
          <div class="form-field">
            <label>{{ $t('events.config.ruleType') }}</label>
            <v-select
              v-model="rule.rule_type"
              :items="printerRuleTypeOptions"
              item-title="label"
              item-value="value"
              density="compact"
              hide-details
            />
          </div>
          <template v-if="rule.rule_type === 'table_range'">
            <div class="rule-range-row">
              <div class="form-field">
                <label>{{ $t('events.config.tableFrom') }}</label>
                <v-text-field
                  v-model.number="rule.table_from"
                  type="number"
                  min="1"
                  max="99999"
                  density="compact"
                  hide-details
                />
              </div>
              <div class="form-field">
                <label>{{ $t('events.config.tableTo') }}</label>
                <v-text-field
                  v-model.number="rule.table_to"
                  type="number"
                  min="1"
                  max="99999"
                  density="compact"
                  hide-details
                />
              </div>
            </div>
          </template>
          <div v-else-if="rule.rule_type === 'pickup_prefix'" class="form-field">
            <label>{{ $t('events.config.pickupPrefix') }}</label>
            <v-text-field
              v-model="rule.pickup_prefix"
              :placeholder="$t('events.config.pickupPrefixPlaceholder')"
              maxlength="3"
              density="compact"
              hide-details
              @update:model-value="rule.pickup_prefix = normalizePickupPrefix($event)"
            />
          </div>
          <div class="form-field">
            <label>{{ $t('events.config.printer') }}</label>
            <v-select
              v-model="rule.printer_appliance_id"
              :items="printerOptions"
              item-title="name"
              item-value="id"
              :placeholder="$t('events.config.noPrinter')"
              clearable
              density="compact"
              hide-details
            />
          </div>
        </div>
      </div>
      <div class="form-field">
        <label>{{ $t('events.config.articles') }}</label>
        <v-select
          v-model="st.article_ids"
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
    </div>
    <p v-if="!stations.length" class="muted">{{ $t('events.config.noStations') }}</p>
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
import FormLabel from './FormLabel.vue'
import { rules } from '../utils/formRules.js'

defineProps({
  catalogLoading: {
    type: Boolean,
    default: false,
  },
  catalogError: {
    type: String,
    default: '',
  },
  printerOptions: {
    type: Array,
    default: () => [],
  },
  articleOptions: {
    type: Array,
    default: () => [],
  },
  alternativePrintersEnabled: {
    type: Boolean,
    default: false,
  },
  printerRuleTypeOptions: {
    type: Array,
    default: () => [],
  },
})

const stations = defineModel({ type: Array, required: true })

const { t } = useI18n()

function normalizePickupPrefix(value) {
  return String(value || '').toUpperCase().replace(/[^A-Z]/g, '').slice(0, 3)
}

function addStation() {
  stations.value.push({
    name: t('events.config.stationFallback', { n: stations.value.length + 1 }),
    printer_appliance_id: null,
    printer_rules: [],
    article_ids: [],
  })
}

function removeStation(idx) {
  stations.value.splice(idx, 1)
}

function addPrinterRule(stationIdx) {
  const st = stations.value[stationIdx]
  if (!st) return
  if (!Array.isArray(st.printer_rules)) st.printer_rules = []
  st.printer_rules.push({
    rule_type: 'table_range',
    table_from: 1,
    table_to: 50,
    pickup_prefix: 'A',
    printer_appliance_id: null,
  })
}

function removePrinterRule(stationIdx, ruleIdx) {
  const st = stations.value[stationIdx]
  if (!st?.printer_rules) return
  st.printer_rules.splice(ruleIdx, 1)
}
</script>

<style scoped>
.printer-rules-block {
  margin-bottom: 0.75rem;
}

.printer-rules-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.printer-rule-card {
  border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
  padding: 0.75rem;
  margin-bottom: 0.75rem;
  background: rgb(var(--v-theme-surface));
}

.printer-rule-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
  font-weight: 600;
  font-size: 0.875rem;
}

.rule-range-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

@media (max-width: 992px) {
  .rule-range-row {
    grid-template-columns: 1fr;
  }
}
</style>
