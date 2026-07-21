<template>
  <div class="event-config-layouts-section">
    <p v-if="layoutCellsLoading" class="muted catalog-loading-hint">{{ $t('events.config.layoutCellsLoading') }}</p>
    <p v-else-if="layoutCellsError" class="error">{{ layoutCellsError }}</p>
    <div v-if="!layoutCellsLoading && layoutCellsLoaded" class="section-toolbar">
      <v-btn color="primary" type="button" @click="addLayout">{{ $t('events.config.addLayout') }}</v-btn>
    </div>
    <div
      v-for="(lo, li) in layouts"
      v-show="!layoutCellsLoading && layoutCellsLoaded"
      :key="'lo-' + li"
      class="config-card"
    >
      <div class="config-card-header">
        <span>{{ $t('events.config.layoutN', { n: li + 1 }) }}</span>
        <div class="layout-header-actions">
          <v-checkbox
            :model-value="lo.is_default"
            :label="$t('events.config.default')"
            hide-details
            density="compact"
            @update:model-value="(v) => onDefaultLayoutChange(li, v)"
          />
          <v-btn icon="mdi-delete" variant="text" color="error" type="button" @click="removeLayout(li)" />
        </div>
      </div>
      <div class="field-row">
        <div class="form-field">
          <label>{{ $t('events.config.name') }}</label>
          <v-text-field v-model="lo.name" :placeholder="$t('events.config.optional')" density="compact" hide-details />
        </div>
        <div class="form-field">
          <label>{{ $t('events.config.width') }}</label>
          <v-number-input
            :model-value="lo.grid_width"
            :min="1"
            :max="64"
            control-variant="stacked"
            density="compact"
            hide-details
            @update:model-value="(v) => onGridWidthChange(lo, v)"
          />
        </div>
        <div class="form-field">
          <label>{{ $t('events.config.height') }}</label>
          <v-number-input
            :model-value="lo.grid_height"
            :min="1"
            :max="64"
            control-variant="stacked"
            density="compact"
            hide-details
            @update:model-value="(v) => onGridHeightChange(lo, v)"
          />
        </div>
      </div>
      <p class="muted small">{{ $t('events.config.clickCellsToEdit') }}</p>
      <div class="layout-grid-wrap">
        <div
          class="layout-grid"
          :style="{
            gridTemplateColumns: `repeat(${lo.grid_width}, minmax(0, 1fr))`,
            gridTemplateRows: `repeat(${lo.grid_height}, minmax(2.5rem, auto))`,
          }"
        >
          <button
            v-for="pos in gridPositions(lo)"
            :key="li + '-' + pos.row + '-' + pos.col"
            type="button"
            class="grid-cell"
            :style="previewCellStyle(displayCell(lo, pos.row, pos.col))"
            @click="openCellDialog(li, pos.row, pos.col)"
          >
            <span class="grid-cell-label">{{ displayCell(lo, pos.row, pos.col).label || '·' }}</span>
            <span v-if="cellPreviewMeta(lo, pos.row, pos.col)" class="grid-cell-count">
              {{ cellPreviewMeta(lo, pos.row, pos.col) }}
            </span>
          </button>
        </div>
      </div>
    </div>

    <v-dialog v-model="cellDialogVisible" max-width="32rem" class="cell-dialog">
      <v-card>
        <v-card-title>{{ $t('events.config.editCell') }}</v-card-title>
        <v-card-text>
          <div class="form-field">
            <label>{{ $t('events.config.label') }}</label>
            <v-text-field v-model="cellEdit.label" density="compact" hide-details />
          </div>
          <div class="form-field">
            <label>{{ $t('events.config.color') }}</label>
            <div v-if="paletteColors.length" class="org-palette-colors">
              <p class="muted small">{{ $t('events.config.orgColorPalette') }}</p>
              <div class="org-palette-swatches">
                <button
                  v-for="entry in paletteColors"
                  :key="entry.label + entry.color"
                  type="button"
                  class="org-palette-swatch"
                  :class="{ selected: cellEdit.color.toUpperCase() === entry.color.toUpperCase() }"
                  @click="cellEdit.color = entry.color"
                >
                  <span class="org-palette-swatch-color" :style="{ background: entry.color }" />
                  <span class="org-palette-swatch-label">{{ entry.label }}</span>
                </button>
              </div>
            </div>
            <v-color-picker v-model="cellEdit.color" mode="hex" hide-inputs />
            <v-text-field
              v-model="cellEdit.color"
              density="compact"
              hide-details
              placeholder="#eeeeee"
              class="color-hex-input"
            />
          </div>
          <div v-if="vouchersEnabled" class="form-field">
            <label>{{ $t('events.config.fixedAmountVouchers') }}</label>
            <v-select
              v-model="cellEdit.voucher_definition_uuids"
              :items="fixedAmountVoucherOptions"
              item-title="label"
              item-value="value"
              :placeholder="$t('events.config.selectVouchers')"
              multiple
              chips
              closable-chips
              density="compact"
              hide-details
            />
          </div>
          <div class="form-field">
            <label>{{ $t('events.config.stationArticlesOnly') }}</label>
            <v-text-field
              v-model="cellTreeFilter"
              :placeholder="$t('events.config.filterArticles')"
              prepend-inner-icon="mdi-magnify"
              density="compact"
              hide-details
              clearable
              class="tree-filter"
            />
            <v-progress-linear v-if="treeLoading" indeterminate color="primary" class="tree-loading" />
            <p
              v-else-if="treeError"
              data-testid="cell-article-tree-error"
              class="error"
            >
              {{ treeError }}
            </p>
            <p
              v-else-if="!filteredCellTreeItems.length"
              data-testid="cell-article-tree-empty"
              class="muted empty-hint"
            >
              {{ $t('events.config.noStationArticlesForCell') }}
            </p>
            <v-treeview
              v-else
              v-model:selected="cellTreeSelection"
              :items="filteredCellTreeItems"
              item-value="key"
              item-title="title"
              item-children="children"
              selectable
              select-strategy="leaf"
              open-all
              density="compact"
              class="cell-article-tree"
            />
          </div>
        </v-card-text>
        <v-card-actions class="dialog-actions">
          <v-btn
            v-if="cellDialogHadContent"
            data-testid="delete-layout-cell-btn"
            color="error"
            variant="text"
            type="button"
            @click="deleteCellDialog"
          >
            {{ $t('events.config.deleteCell') }}
          </v-btn>
          <v-spacer />
          <v-btn variant="outlined" type="button" @click="cellDialogVisible = false">{{ $t('common.cancel') }}</v-btn>
          <v-btn color="primary" type="button" @click="applyCellDialog">{{ $t('events.config.apply') }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { apiJson } from '../api'
import { textColorForBackground } from '../utils/colorContrast.js'
import { filterTreeNodes, mapTreeNodes, buildArticleCategoryTree } from '../utils/articleCategoryTree'
import { layoutCellHasContent } from '../utils/eventConfigLayoutsPayload'
import { newUuid } from '@/utils/newUuid'
import type { ArticleRead, ColorPaletteEntry, EventConfigurationRead } from '@/types/api'
import type {
  EventCellEditState,
  EventLayoutCellLocal,
  EventLayoutLocal,
  EventVoucherDefinitionLocal,
  LayoutRemovedPayload,
  StationArticleTreeNode,
  StationArticleTreeResponse,
} from '@/types/ui'

const props = withDefaults(
  defineProps<{
    eventId: number
    organisationId?: number | null
    vouchersEnabled?: boolean
    voucherDefinitions?: EventVoucherDefinitionLocal[]
    /** Station-assigned org articles for the cell picker; when set, skips the tree API. */
    eventArticles?: ArticleRead[] | null
  }>(),
  {
    organisationId: null,
    vouchersEnabled: false,
    voucherDefinitions: () => [],
    eventArticles: undefined,
  },
)

const emit = defineEmits<{
  'layout-removed': [payload: LayoutRemovedPayload]
}>()
const layouts = defineModel<EventLayoutLocal[]>({ required: true })
const cellDialogVisible = defineModel<boolean>('cellDialogOpen', { default: false })

const { t } = useI18n()

const layoutCellsLoaded = ref(false)
const layoutCellsLoading = ref(false)
const layoutCellsError = ref('')
const paletteColors = ref<ColorPaletteEntry[]>([])

const cellEditLayoutIndex = ref(0)
const cellEditRow = ref(0)
const cellEditCol = ref(0)
const cellEdit = ref<EventCellEditState>({
  label: '',
  color: '#eeeeee',
  article_ids: [],
  voucher_definition_uuid: null,
  voucher_definition_uuids: [],
})
const cellTreeNodesRaw = ref<StationArticleTreeNode[]>([])
const cellTreeSelection = ref<string[]>([])
const cellTreeFilter = ref('')
const treeLoading = ref(false)
const treeError = ref('')
const cellDialogHadContent = ref(false)

const fixedAmountVoucherOptions = computed(() =>
  props.voucherDefinitions
    .filter((vd) => vd.kind === 'fixed_amount' && vd.uuid)
    .map((vd) => ({
      label: vd.name || t('events.config.voucherFallback'),
      value: vd.uuid,
    })),
)

const cellTreeItems = computed(() => mapTreeNodes(cellTreeNodesRaw.value))

const filteredCellTreeItems = computed(() => {
  const q = cellTreeFilter.value.trim().toLowerCase()
  if (!q) return cellTreeItems.value
  return filterTreeNodes(cellTreeItems.value, q)
})

function cellVoucherUuids(c: EventLayoutCellLocal | null | undefined): string[] {
  const list = c?.voucher_definition_uuids
  if (Array.isArray(list) && list.length) return list.map(String)
  if (c?.voucher_definition_uuid) return [String(c.voucher_definition_uuid)]
  return []
}

function gridPositions(lo: EventLayoutLocal): Array<{ row: number; col: number }> {
  const out: Array<{ row: number; col: number }> = []
  for (let row = 0; row < lo.grid_height; row += 1) {
    for (let col = 0; col < lo.grid_width; col += 1) {
      out.push({ row, col })
    }
  }
  return out
}

function displayCell(lo: EventLayoutLocal, row: number, col: number): EventLayoutCellLocal {
  const c = lo.cells.find((x) => x.row === row && x.col === col)
  return (
    c || {
      row,
      col,
      label: '',
      color: '#eeeeee',
      article_ids: [],
      voucher_definition_uuid: null,
      voucher_definition_uuids: [],
    }
  )
}

function previewCellStyle(cell: EventLayoutCellLocal): { background: string; color: string } {
  const background = cell.color || '#eeeeee'
  return {
    background,
    color: textColorForBackground(background),
  }
}

function clampGridDim(value: number | string | null | undefined, fallback = 4): number {
  const n = Math.round(Number(value))
  if (!Number.isFinite(n)) return fallback
  return Math.min(64, Math.max(1, n))
}

function isCellInGrid(c: EventLayoutCellLocal, width: number, height: number): boolean {
  return c.row >= 0 && c.col >= 0 && c.row < height && c.col < width
}

function cellHasData(c: EventLayoutCellLocal): boolean {
  if ((c.label || '').trim()) return true
  if ((c.article_ids || []).length > 0) return true
  if (cellVoucherUuids(c).length > 0) return true
  const color = (c.color || '').toLowerCase()
  if (color && color !== '#eeeeee' && color !== '#eee') return true
  return false
}

function applyGridSizeChange(lo: EventLayoutLocal, nextW: number | string | null | undefined, nextH: number | string | null | undefined): boolean {
  const prevW = lo.grid_width
  const prevH = lo.grid_height
  nextW = clampGridDim(nextW, prevW)
  nextH = clampGridDim(nextH, prevH)
  if (nextW === prevW && nextH === prevH) return true

  if (nextW >= prevW && nextH >= prevH) {
    lo.grid_width = nextW
    lo.grid_height = nextH
    return true
  }

  if (!Array.isArray(lo.cells)) lo.cells = []

  lo.cells = lo.cells.filter((c) => {
    if (isCellInGrid(c, nextW, nextH)) return true
    return !cellHasData(c)
  })

  const oobWithData = lo.cells.filter((c) => !isCellInGrid(c, nextW, nextH) && cellHasData(c))
  if (oobWithData.length) {
    const examples = oobWithData
      .slice(0, 3)
      .map((c) => t('events.config.gridRowCol', { row: c.row + 1, col: c.col + 1 }))
      .join('; ')
    const more = oobWithData.length > 3 ? t('events.config.gridConfirmMore') : ''
    const msg =
      oobWithData.length === 1
        ? t('events.config.gridConfirmSingle', { examples })
        : t('events.config.gridConfirmMultiple', { count: oobWithData.length, examples, more })
    if (!confirm(msg)) return false
    lo.cells = lo.cells.filter((c) => isCellInGrid(c, nextW, nextH))
  }

  lo.grid_width = nextW
  lo.grid_height = nextH
  return true
}

function onGridWidthChange(lo: EventLayoutLocal, value: number | string | null | undefined) {
  applyGridSizeChange(lo, value, lo.grid_height)
}

function onGridHeightChange(lo: EventLayoutLocal, value: number | string | null | undefined) {
  applyGridSizeChange(lo, lo.grid_width, value)
}

function cellPreviewMeta(lo: EventLayoutLocal, row: number, col: number): string {
  const c = displayCell(lo, row, col)
  const vCount = cellVoucherUuids(c).length
  const aCount = c.article_ids?.length || 0
  const parts: string[] = []
  if (vCount) parts.push(t('events.config.voucherCount', { count: vCount }))
  if (aCount) parts.push(t('events.config.articleCount', { count: aCount }))
  return parts.join(' · ')
}

function ensureCell(lo: EventLayoutLocal, row: number, col: number): EventLayoutCellLocal {
  let c = lo.cells.find((x) => x.row === row && x.col === col)
  if (!c) {
    c = {
      row,
      col,
      label: '',
      color: '#eeeeee',
      article_ids: [],
      voucher_definition_uuid: null,
      voucher_definition_uuids: [],
    }
    lo.cells.push(c)
  }
  return c
}

function removeCellAt(lo: EventLayoutLocal, row: number, col: number) {
  lo.cells = lo.cells.filter((c) => !(c.row === row && c.col === col))
}

function buildCellFromDialog(row: number, col: number): EventLayoutCellLocal {
  const vUuids = [...(cellEdit.value.voucher_definition_uuids || [])]
  return {
    row,
    col,
    label: cellEdit.value.label || '',
    color: cellEdit.value.color || '#eeeeee',
    voucher_definition_uuids: vUuids,
    voucher_definition_uuid: vUuids[0] || null,
    article_ids: treeSelectionToArticleIds(cellTreeSelection.value),
  }
}

function articleIdsToTreeSelection(ids: number[]): string[] {
  return (ids || []).map((id) => `art-${id}`)
}

function treeSelectionToArticleIds(sel: string[]): number[] {
  if (!Array.isArray(sel)) return []
  return sel
    .filter((k) => typeof k === 'string' && k.startsWith('art-'))
    .map((k) => Number(k.replace(/^art-/, '')))
    .filter((n) => !Number.isNaN(n))
}

function ensureDefaultLayout() {
  if (!layouts.value.length) {
    layouts.value.push({
      uuid: newUuid(),
      name: t('events.config.defaultLayoutName'),
      is_default: true,
      grid_width: 4,
      grid_height: 4,
      cells: [],
    })
  }
}

function setOnlyDefault(idx: number) {
  layouts.value.forEach((lo, i) => {
    lo.is_default = i === idx
  })
}

function onDefaultLayoutChange(layoutIndex: number, checked: boolean | null) {
  if (checked) {
    setOnlyDefault(layoutIndex)
  } else {
    const lo = layouts.value[layoutIndex]
    if (lo) lo.is_default = false
    if (!layouts.value.some((l) => l.is_default)) {
      const first = layouts.value[0]
      if (first) first.is_default = true
    }
  }
}

function addLayout() {
  layouts.value.push({
    uuid: newUuid(),
    name: t('events.config.layoutN', { n: layouts.value.length + 1 }),
    is_default: false,
    grid_width: 4,
    grid_height: 4,
    cells: [],
  })
}

function removeLayout(idx: number) {
  const removed = layouts.value[idx]
  layouts.value.splice(idx, 1)
  if (!layouts.value.some((l) => l.is_default) && layouts.value.length) {
    layouts.value[0].is_default = true
  }
  if (removed) {
    emit('layout-removed', {
      removedUuid: removed.uuid,
      fallbackUuid: layouts.value[0]?.uuid || '',
    })
  }
}

function mapLayoutCells(cells: EventLayoutCellLocal[] | undefined) {
  return (cells || []).map((c) => ({
    row: c.row,
    col: c.col,
    label: c.label || '',
    color: c.color || '#eeeeee',
    article_ids: [...(c.article_ids || [])],
    voucher_definition_uuid: c.voucher_definition_uuid || null,
    voucher_definition_uuids: [...cellVoucherUuids(c)],
  }))
}

function mergeLayoutCellsFromResponse(cfg: EventConfigurationRead) {
  const remoteByUuid = new Map((cfg.app_layouts || []).map((lo) => [lo.uuid, lo]))
  layouts.value = layouts.value.map((lo) => {
    const remote = remoteByUuid.get(lo.uuid)
    if (!remote) return lo
    return {
      ...lo,
      cells: mapLayoutCells(remote.cells as EventLayoutCellLocal[]),
    }
  })
  layoutCellsLoaded.value = true
}

async function loadLayoutCells() {
  if (layoutCellsLoaded.value || layoutCellsLoading.value) return
  layoutCellsLoading.value = true
  layoutCellsError.value = ''
  try {
    mergeLayoutCellsFromResponse(
      await apiJson<EventConfigurationRead>(`/events/${props.eventId}/configuration`),
    )
  } catch {
    layoutCellsError.value = t('events.config.layoutCellsLoadFailed')
  } finally {
    layoutCellsLoading.value = false
  }
}

async function openCellDialog(layoutIndex: number, row: number, col: number) {
  cellEditLayoutIndex.value = layoutIndex
  cellEditRow.value = row
  cellEditCol.value = col
  cellTreeFilter.value = ''
  treeError.value = ''
  const lo = layouts.value[layoutIndex]
  const c = displayCell(lo, row, col)
  cellDialogHadContent.value = layoutCellHasContent(c)
  const vUuids = cellVoucherUuids(c)
  cellEdit.value = {
    label: c.label || '',
    color: c.color || '#eeeeee',
    article_ids: [...(c.article_ids || [])],
    voucher_definition_uuid: vUuids[0] || null,
    voucher_definition_uuids: [...vUuids],
  }
  cellTreeSelection.value = articleIdsToTreeSelection(c.article_ids)
  cellDialogVisible.value = true

  if (props.eventArticles != null) {
    treeLoading.value = false
    cellTreeNodesRaw.value = buildArticleCategoryTree(props.eventArticles)
    return
  }

  treeLoading.value = true
  cellTreeNodesRaw.value = []
  try {
    const data = await apiJson<StationArticleTreeResponse>(
      `/events/${props.eventId}/station-article-tree`,
    )
    cellTreeNodesRaw.value = data.nodes || []
  } catch {
    cellTreeNodesRaw.value = []
    treeError.value = t('events.config.stationArticleTreeLoadFailed')
  } finally {
    treeLoading.value = false
  }
}

function applyCellDialog() {
  const lo = layouts.value[cellEditLayoutIndex.value]
  const row = cellEditRow.value
  const col = cellEditCol.value
  const updated = buildCellFromDialog(row, col)
  if (!layoutCellHasContent(updated)) {
    removeCellAt(lo, row, col)
  } else {
    const c = ensureCell(lo, row, col)
    c.label = updated.label
    c.color = updated.color
    c.voucher_definition_uuids = updated.voucher_definition_uuids
    c.voucher_definition_uuid = updated.voucher_definition_uuid
    c.article_ids = updated.article_ids
  }
  cellDialogHadContent.value = false
  cellDialogVisible.value = false
}

function deleteCellDialog() {
  if (!confirm(t('events.config.deleteCellConfirm'))) return
  const lo = layouts.value[cellEditLayoutIndex.value]
  removeCellAt(lo, cellEditRow.value, cellEditCol.value)
  cellDialogHadContent.value = false
  cellDialogVisible.value = false
}

function resetLayoutCellsState() {
  layoutCellsLoaded.value = false
  layoutCellsLoading.value = false
  layoutCellsError.value = ''
}

async function loadPaletteColors() {
  paletteColors.value = []
  const orgId = props.organisationId
  if (!orgId) return
  try {
    const data = await apiJson<{ colors?: ColorPaletteEntry[] }>(`/organisations/${orgId}/color-palette`)
    paletteColors.value = data.colors ?? []
  } catch {
    paletteColors.value = []
  }
}

watch(
  () => props.eventId,
  () => {
    resetLayoutCellsState()
    void loadLayoutCells()
  },
)

watch(
  () => props.organisationId,
  () => {
    void loadPaletteColors()
  },
  { immediate: true },
)

onMounted(() => {
  void loadLayoutCells()
})

defineExpose({
  loadLayoutCells,
  ensureDefaultLayout,
  resetLayoutCellsState,
  isCellInGrid,
  cellVoucherUuids,
  layoutCellsLoaded,
  layoutCellsLoading,
})
</script>

<style scoped>
.layout-header-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.muted.small {
  font-size: 0.85rem;
  margin: 0.25rem 0 0.75rem;
}

.layout-grid-wrap {
  overflow: auto;
  max-width: 100%;
}

.layout-grid {
  display: grid;
  gap: 4px;
  min-width: min-content;
}

.grid-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.15rem;
  border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
  cursor: pointer;
  padding: 0.35rem;
  min-height: 2.5rem;
  text-align: center;
}

.grid-cell-label {
  font-size: 0.75rem;
  word-break: break-word;
}

.grid-cell-count {
  font-size: 0.65rem;
  opacity: 0.65;
  line-height: 1.1;
}

.org-palette-colors {
  margin-bottom: 0.75rem;
}

.org-palette-swatches {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.org-palette-swatch {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.2rem;
  border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
  background: transparent;
  cursor: pointer;
  padding: 0.35rem;
  min-width: 4.5rem;
}

.org-palette-swatch.selected {
  border-color: rgb(var(--v-theme-primary));
  box-shadow: 0 0 0 1px rgb(var(--v-theme-primary));
}

.org-palette-swatch-color {
  width: 2rem;
  height: 2rem;
  border-radius: 6px;
  border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.org-palette-swatch-label {
  font-size: 0.7rem;
  text-align: center;
  line-height: 1.1;
  max-width: 5rem;
  word-break: break-word;
}

.color-hex-input {
  max-width: 10rem;
  margin-top: 0.35rem;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.tree-filter {
  margin-bottom: 0.5rem;
}

.tree-loading {
  margin-top: 0.5rem;
}

.cell-article-tree {
  max-height: 280px;
  overflow-y: auto;
}

.empty-hint {
  margin: 0.5rem 0 0;
  font-size: 0.875rem;
}

.dialog-actions {
  padding: 0.75rem 1rem 1rem;
}

@media (max-width: 992px) {
  .layout-header-actions {
    flex-wrap: wrap;
    width: 100%;
  }
}
</style>
