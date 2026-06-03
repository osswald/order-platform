<template>
  <Teleport to="body">
    <div v-if="open" class="sheet-backdrop sheet-backdrop--actions" @click.self="close" />
    <div v-if="open" class="sheet sheet--actions" role="dialog" aria-modal="true">
      <header class="sheet-header">
        <h3>{{ stepTitle }}</h3>
        <button v-if="step !== 'types'" type="button" class="link-back" @click="step = 'types'">← Zurück</button>
      </header>

      <template v-if="step === 'types'">
        <p v-if="!definitions.length" class="muted">Keine Gutschein-Typen konfiguriert.</p>
        <ul v-else class="pick-list">
          <li v-for="vd in definitions" :key="vd.uuid">
            <button type="button" class="pick-row" @click="pickType(vd)">
              <span class="name">{{ vd.name }}</span>
              <span class="meta muted">{{ typeHint(vd) }}</span>
            </button>
          </li>
        </ul>
        <button type="button" class="btn" style="width: 100%" @click="close">Abbrechen</button>
      </template>

      <template v-else-if="step === 'amount-confirm'">
        <p class="confirm-text">
          Gutschrift auf Teilbetrag: <strong>{{ formatAmount(creditPreview) }}</strong>
        </p>
        <button type="button" class="btn primary" style="width: 100%" @click="confirmAmount">Übernehmen</button>
        <button type="button" class="btn" style="width: 100%; margin-top: 0.5rem" @click="close">Abbrechen</button>
      </template>

      <template v-else-if="step === 'pick-line'">
        <p class="muted confirm-text">Position für «{{ pendingType?.name }}» wählen:</p>
        <ul class="pick-list">
          <li v-for="(sel, idx) in eligibleSelections" :key="idx">
            <button type="button" class="pick-row" @click="confirmArticle(sel)">
              <span class="name">{{ sel.label }}</span>
              <span class="meta muted">{{ formatAmount(sel.unit_cents) }}</span>
            </button>
          </li>
        </ul>
        <button type="button" class="btn" style="width: 100%" @click="close">Abbrechen</button>
      </template>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useEventContext } from '../composables/useEventContext'
import { formatAmount, voucherEntitlementCreditCents } from '../utils/money'
import { lineAdditionLabels, voucherDefinitionsForEvent } from '../utils/bundleHelpers'

const { showToast } = useEventContext()

const props = defineProps({
  open: Boolean,
  event: { type: Object, default: null },
  grossCents: { type: Number, default: 0 },
  selections: { type: Array, default: () => [] },
  lineGroups: { type: Array, default: () => [] },
})

const emit = defineEmits(['close', 'apply'])

const step = ref('types')
const pendingType = ref(null)

const definitions = computed(() => voucherDefinitionsForEvent(props.event))

const stepTitle = computed(() => {
  if (step.value === 'types') return 'Gutschein einlösen'
  if (step.value === 'amount-confirm') return pendingType.value?.name || 'Betrags-Gutschein'
  return 'Artikel wählen'
})

const creditPreview = computed(() => {
  const vd = pendingType.value
  if (!vd || vd.kind !== 'fixed_amount') return 0
  const face = Math.max(0, Number(vd.value_cents) || 0)
  return Math.min(props.grossCents, face)
})

function typeHint(vd) {
  if (vd.kind === 'fixed_amount') {
    return formatAmount(vd.value_cents || 0)
  }
  return 'Artikel-Gutschein'
}

function selectionLabel(sel, arts) {
  const a = arts[String(sel.article_id)] || arts[sel.article_id]
  const base = a?.name || `Artikel #${sel.article_id}`
  const adds = lineAdditionLabels(sel, arts)
  if (!adds.length) return base
  const hint = adds.map((x) => x.name).join(', ')
  return `${base} (+ ${hint})`
}

const eligibleSelections = computed(() => {
  const vd = pendingType.value
  if (!vd || vd.kind !== 'article_entitlement') return []
  const allowed = new Set((vd.allowed_article_ids || []).map(Number))
  const arts = props.event?.articles || {}
  return (props.selections || [])
    .filter((s) => allowed.has(Number(s.article_id)))
    .map((s) => ({
      ...s,
      label: selectionLabel(s, arts),
      unit_cents: voucherEntitlementCreditCents(s, arts, vd, props.event, props.lineGroups),
    }))
})

function pickType(vd) {
  pendingType.value = vd
  if (vd.kind === 'fixed_amount') {
    step.value = 'amount-confirm'
    return
  }
  if (!eligibleSelections.value.length) {
    step.value = 'pick-line'
    return
  }
  if (eligibleSelections.value.length === 1) {
    confirmArticle(eligibleSelections.value[0])
    return
  }
  step.value = 'pick-line'
}

function confirmAmount() {
  const vd = pendingType.value
  if (!vd) return
  emit('apply', {
    voucher_definition_uuid: vd.uuid,
    kind: vd.kind,
    applied_cents: creditPreview.value,
  })
  close()
}

function confirmArticle(sel) {
  const vd = pendingType.value
  if (!vd) return
  const arts = props.event?.articles || {}
  const applied = voucherEntitlementCreditCents(sel, arts, vd, props.event, props.lineGroups)
  if (applied <= 0) {
    showToast('Position nicht gefunden', 'err')
    return
  }
  emit('apply', {
    voucher_definition_uuid: vd.uuid,
    kind: vd.kind,
    applied_cents: applied,
    article_id: sel.article_id,
    note: sel.note || '',
    qty: 1,
    additions: sel.additions || [],
  })
  close()
}

function close() {
  emit('close')
}

watch(
  () => props.open,
  (v) => {
    if (v) {
      step.value = 'types'
      pendingType.value = null
    }
  },
)
</script>

<style scoped>
.sheet-backdrop--actions {
  z-index: 150;
}

.sheet--actions {
  z-index: 151;
}

.sheet-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.sheet-header h3 {
  margin: 0;
  font-size: 1rem;
}

.link-back {
  border: none;
  background: none;
  color: var(--primary);
  font-size: 0.95rem;
  cursor: pointer;
}

.pick-list {
  list-style: none;
  padding: 0;
  margin: 0 0 1rem;
  max-height: 40vh;
  overflow-y: auto;
}

.pick-row {
  width: 100%;
  text-align: left;
  padding: 0.75rem 1rem;
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  background: var(--bg);
  color: var(--text);
  margin-bottom: 0.5rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
  cursor: pointer;
  touch-action: manipulation;
}

.pick-row .name {
  font-weight: 600;
}

.confirm-text {
  margin: 0 0 1rem;
}
</style>
