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
        <SheetOptionList v-else :items="typeListItems" max-height="40vh" @pick="onPickType" />
        <button type="button" class="btn" style="width: 100%" @click="close">Abbrechen</button>
      </template>

      <template v-else-if="step === 'amount-confirm'">
        <p class="confirm-text">
          Gutschrift auf Teilbetrag: <strong>{{ formatMoney(creditPreview, eventCurrency) }}</strong>
        </p>
        <button type="button" class="btn primary" style="width: 100%" @click="confirmAmount">Übernehmen</button>
        <button type="button" class="btn" style="width: 100%; margin-top: 0.5rem" @click="close">Abbrechen</button>
      </template>

      <template v-else-if="step === 'pick-line'">
        <p class="muted confirm-text">Position für «{{ pendingType?.name }}» wählen:</p>
        <SheetOptionList :items="lineListItems" max-height="40vh" @pick="confirmArticle" />
        <button type="button" class="btn" style="width: 100%" @click="close">Abbrechen</button>
      </template>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useEventContext } from '@/composables/useEventContext'
import type {
  EdgeBundleEvent,
  LineGroupEntry,
  LineSelection,
} from '@/types/api'
import { formatMoney, voucherEntitlementCreditCents } from '@/utils/money'
import { voucherDefinitionsForEvent } from '@/utils/bundleHelpers'
import {
  asArticleLineSelection,
  type ArticleLineSelection,
  voucherRedeemSelectionLabel,
} from '@/utils/voucherRedeemSelection'
import SheetOptionList, { type SheetOptionItem } from './SheetOptionList.vue'

interface VoucherDefinition {
  uuid: string
  name?: string
  kind?: string
  value_cents?: number
  allowed_article_ids?: number[]
  include_additions?: boolean
}

interface EligibleSelection extends ArticleLineSelection {
  label: string
  unit_cents: number
}

interface VoucherApplyPayload {
  voucher_definition_uuid: string
  kind?: string
  applied_cents: number
  article_id?: number
  note?: string
  qty?: number
  additions?: LineSelection['additions']
}

const { showToast } = useEventContext()

const props = withDefaults(
  defineProps<{
    open?: boolean
    event?: EdgeBundleEvent | null
    grossCents?: number
    selections?: LineSelection[]
    lineGroups?: LineGroupEntry[]
  }>(),
  {
    open: false,
    event: null,
    grossCents: 0,
    selections: () => [],
    lineGroups: () => [],
  },
)

const emit = defineEmits<{
  close: []
  apply: [payload: VoucherApplyPayload]
}>()

const step = ref('types')
const pendingType = ref<VoucherDefinition | null>(null)

const definitions = computed(
  () => voucherDefinitionsForEvent(props.event) as unknown as VoucherDefinition[],
)

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

const typeListItems = computed(() =>
  definitions.value.map((vd) => ({
    key: vd.uuid,
    label: vd.name,
    meta: typeHint(vd),
    vd,
  })),
)

const eventCurrency = computed(() => props.event?.currency || 'CHF')

function typeHint(vd: VoucherDefinition) {
  if (vd.kind === 'fixed_amount') {
    return formatMoney(vd.value_cents || 0, eventCurrency.value)
  }
  return 'Artikel-Gutschein'
}

const eligibleSelections = computed((): EligibleSelection[] => {
  const vd = pendingType.value
  if (!vd || vd.kind !== 'article_entitlement') return []
  const allowed = new Set((vd.allowed_article_ids || []).map(Number))
  const arts = props.event?.articles || {}
  const out: EligibleSelection[] = []
  for (const raw of props.selections || []) {
    const s = asArticleLineSelection(raw)
    if (!s || !allowed.has(s.article_id)) continue
    out.push({
      ...s,
      label: voucherRedeemSelectionLabel(s, arts),
      unit_cents: voucherEntitlementCreditCents(s, arts, vd, props.event, props.lineGroups),
    })
  }
  return out
})

const lineListItems = computed(() =>
  eligibleSelections.value.map((sel, idx) => ({
    key: idx,
    label: sel.label,
    meta: formatMoney(sel.unit_cents, eventCurrency.value),
    sel,
  })),
)

function onPickType(item: SheetOptionItem & { vd?: VoucherDefinition }) {
  if (item.vd) pickType(item.vd)
}

function pickType(vd: VoucherDefinition) {
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
    confirmArticle({ sel: eligibleSelections.value[0] })
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

function confirmArticle(item: SheetOptionItem & { sel?: EligibleSelection } | EligibleSelection) {
  const sel = 'sel' in item && item.sel ? item.sel : (item as EligibleSelection)
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

.confirm-text {
  margin: 0 0 1rem;
}
</style>
