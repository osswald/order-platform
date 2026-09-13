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
          <v-btn icon="mdi-delete" color="error" type="button" @click="removeLayout(li)" />
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
            :class="gridCellClass(lo, li, pos.row, pos.col)"
            :data-layout-index="li"
            :data-row="pos.row"
            :data-col="pos.col"
            :style="previewCellStyle(displayCell(lo, pos.row, pos.col))"
            @pointerdown="onGridCellPointerDown($event, li, pos.row, pos.col)"
            @pointermove="onGridCellPointerMove($event)"
            @pointerup="onGridCellPointerUp($event)"
            @pointercancel="onGridCellPointerCancel"
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
          <div
            v-if="showLockedAdditions"
            data-testid="locked-additions"
            class="form-field"
          >
            <label>{{ $t('events.config.lockedAdditions') }}</label>
            <p class="muted small">{{ $t('events.config.lockedAdditionsHint') }}</p>
            <v-progress-linear
              v-if="lockedAdditionsLoading"
              indeterminate
              color="primary"
              class="tree-loading"
            />
            <p v-else-if="!lockedAdditionOptions.length" class="muted empty-hint">
              {{ $t('events.config.lockedAdditionsEmpty') }}
            </p>
            <div v-else class="locked-additions-list">
              <v-checkbox
                v-for="opt in lockedAdditionOptions"
                :key="opt.addition_article_id"
                :model-value="cellEdit.locked_addition_ids.includes(opt.addition_article_id)"
                :label="opt.name"
                hide-details
                density="compact"
                @update:model-value="(v) => toggleLockedAddition(opt.addition_article_id, v === true)"
              />
            </div>
          </div>
        </v-card-text>
        <v-card-actions class="dialog-actions">
          <v-btn
            v-if="cellDialogHadContent"
            data-testid="delete-layout-cell-btn"
            color="error"
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
import {
  cellCanHaveLockedAdditions,
  layoutCellHasContent,
  normalizeLockedAdditionIds,
} from '../utils/eventConfigLayoutsPayload'
import {
  LAYOUT_CELL_DRAG_THRESHOLD_PX,
  layoutCellHasEditorData,
  moveLayoutCell,
} from '../utils/layoutCellMove'
import { newUuid } from '@/utils/newUuid'
import type {
  ArticleAdditionsRead,
  ArticleRead,
  ColorPaletteEntry,
  EventConfigurationRead,
} from '@/types/api'
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
  locked_addition_ids: [],
})
const cellTreeNodesRaw = ref<StationArticleTreeNode[]>([])
const cellTreeSelection = ref<string[]>([])
const cellTreeFilter = ref('')
const treeLoading = ref(false)
const treeError = ref('')
const cellDialogHadContent = ref(false)
const lockedAdditionOptions = ref<Array<{ addition_article_id: number; name: string }>>([])
const lockedAdditionsLoading = ref(false)
let lockedAdditionsRequestId = 0

type GridDragState = {
  layoutIndex: number
  fromRow: number
  fromCol: number
  startX: number
  startY: number
  pointerId: number
  /** Filled cells may become a drag; empty cells only click-to-edit. */
  canDrag: boolean
  dragging: boolean
  hoverRow: number | null
  hoverCol: number | null
}

const gridDrag = ref<GridDragState | null>(null)

const showLockedAdditions = computed(() =>
  cellCanHaveLockedAdditions(
    treeSelectionToArticleIds(cellTreeSelection.value),
    cellEdit.value.voucher_definition_uuids || [],
  ),
)

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
      locked_addition_ids: [],
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
  return layoutCellHasEditorData(c)
}

function gridCellClass(lo: EventLayoutLocal, layoutIndex: number, row: number, col: number) {
  const filled = cellHasData(displayCell(lo, row, col))
  const drag = gridDrag.value
  const classes: Record<string, boolean> = {
    'grid-cell--filled': filled,
  }
  if (!drag || drag.layoutIndex !== layoutIndex) return classes
  if (drag.dragging && drag.fromRow === row && drag.fromCol === col) {
    classes['grid-cell--dragging-source'] = true
  }
  if (drag.dragging && drag.hoverRow === row && drag.hoverCol === col) {
    if (drag.fromRow === row && drag.fromCol === col) {
      // same slot: no special target style
    } else if (filled) {
      classes['grid-cell--drop-blocked'] = true
    } else {
      classes['grid-cell--drop-target'] = true
    }
  }
  return classes
}

function findGridCellFromPoint(clientX: number, clientY: number): HTMLElement | null {
  const el = document.elementFromPoint(clientX, clientY)
  if (!el || !(el instanceof Element)) return null
  const cell = el.closest('.grid-cell')
  return cell instanceof HTMLElement ? cell : null
}

function readGridCellCoords(el: HTMLElement): { layoutIndex: number; row: number; col: number } | null {
  const layoutIndex = Number(el.dataset.layoutIndex)
  const row = Number(el.dataset.row)
  const col = Number(el.dataset.col)
  if (![layoutIndex, row, col].every((n) => Number.isFinite(n))) return null
  return { layoutIndex, row, col }
}

function onGridCellPointerDown(event: PointerEvent, layoutIndex: number, row: number, col: number) {
  if (event.button !== 0) return
  const lo = layouts.value[layoutIndex]
  if (!lo) return
  const target = event.currentTarget
  if (!(target instanceof HTMLElement)) return
  gridDrag.value = {
    layoutIndex,
    fromRow: row,
    fromCol: col,
    startX: event.clientX,
    startY: event.clientY,
    pointerId: event.pointerId,
    canDrag: cellHasData(displayCell(lo, row, col)),
    dragging: false,
    hoverRow: null,
    hoverCol: null,
  }
  try {
    target.setPointerCapture(event.pointerId)
  } catch {
    // jsdom / unsupported capture — drag still works via events on the source
  }
}

function onGridCellPointerMove(event: PointerEvent) {
  const drag = gridDrag.value
  if (!drag || event.pointerId !== drag.pointerId) return
  const dx = event.clientX - drag.startX
  const dy = event.clientY - drag.startY
  if (drag.canDrag && !drag.dragging && Math.hypot(dx, dy) >= LAYOUT_CELL_DRAG_THRESHOLD_PX) {
    drag.dragging = true
  }
  if (!drag.dragging) return
  const under = findGridCellFromPoint(event.clientX, event.clientY)
  const coords = under ? readGridCellCoords(under) : null
  if (coords && coords.layoutIndex === drag.layoutIndex) {
    drag.hoverRow = coords.row
    drag.hoverCol = coords.col
  } else {
    drag.hoverRow = null
    drag.hoverCol = null
  }
}

function clearGridDrag(event?: PointerEvent) {
  const drag = gridDrag.value
  if (drag && event?.currentTarget instanceof HTMLElement) {
    try {
      event.currentTarget.releasePointerCapture(drag.pointerId)
    } catch {
      // ignore
    }
  }
  gridDrag.value = null
}

function onGridCellPointerUp(event: PointerEvent) {
  const drag = gridDrag.value
  if (!drag || event.pointerId !== drag.pointerId) return

  if (drag.dragging) {
    const under = findGridCellFromPoint(event.clientX, event.clientY)
    const coords = under ? readGridCellCoords(under) : null
    if (coords && coords.layoutIndex === drag.layoutIndex) {
      const lo = layouts.value[drag.layoutIndex]
      if (lo) {
        moveLayoutCell(lo, drag.fromRow, drag.fromCol, coords.row, coords.col)
      }
    }
    clearGridDrag(event)
    return
  }

  const { layoutIndex, fromRow, fromCol } = drag
  clearGridDrag(event)
  void openCellDialog(layoutIndex, fromRow, fromCol)
}

function onGridCellPointerCancel(event: PointerEvent) {
  const drag = gridDrag.value
  if (!drag || event.pointerId !== drag.pointerId) return
  clearGridDrag(event)
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
      locked_addition_ids: [],
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
  const articleIds = treeSelectionToArticleIds(cellTreeSelection.value)
  return {
    row,
    col,
    label: cellEdit.value.label || '',
    color: cellEdit.value.color || '#eeeeee',
    voucher_definition_uuids: vUuids,
    voucher_definition_uuid: vUuids[0] || null,
    article_ids: articleIds,
    locked_addition_ids: normalizeLockedAdditionIds(
      articleIds,
      vUuids,
      cellEdit.value.locked_addition_ids,
    ),
  }
}

function toggleLockedAddition(additionArticleId: number, checked: boolean) {
  const current = cellEdit.value.locked_addition_ids || []
  if (checked) {
    if (!current.includes(additionArticleId)) {
      cellEdit.value.locked_addition_ids = [...current, additionArticleId]
    }
    return
  }
  cellEdit.value.locked_addition_ids = current.filter((id) => id !== additionArticleId)
}

async function loadLockedAdditionsForArticle(articleId: number) {
  const requestId = ++lockedAdditionsRequestId
  lockedAdditionsLoading.value = true
  lockedAdditionOptions.value = []
  try {
    const data = await apiJson<ArticleAdditionsRead>(`/articles/${articleId}/additions`)
    if (requestId !== lockedAdditionsRequestId) return
    lockedAdditionOptions.value = (data.items || []).map((row) => ({
      addition_article_id: Number(row.addition_article_id),
      name: String(row.name ?? ''),
    }))
    const available = new Set(
      lockedAdditionOptions.value.map((opt) => opt.addition_article_id),
    )
    cellEdit.value.locked_addition_ids = (cellEdit.value.locked_addition_ids || []).filter(
      (id) => available.has(id),
    )
  } catch {
    if (requestId !== lockedAdditionsRequestId) return
    lockedAdditionOptions.value = []
  } finally {
    if (requestId === lockedAdditionsRequestId) {
      lockedAdditionsLoading.value = false
    }
  }
}

/** Cancel in-flight fetch and clear checklist options without touching selected ids. */
function clearLockedAdditionOptions() {
  lockedAdditionsRequestId += 1
  lockedAdditionOptions.value = []
  lockedAdditionsLoading.value = false
}

function clearLockedAdditionIds() {
  cellEdit.value.locked_addition_ids = []
}

function clearLockedAdditionsUi() {
  clearLockedAdditionOptions()
  clearLockedAdditionIds()
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
  return (cells || []).map((c) => {
    const articleIds = [...(c.article_ids || [])]
    const voucherUuids = [...cellVoucherUuids(c)]
    return {
      row: c.row,
      col: c.col,
      label: c.label || '',
      color: c.color || '#eeeeee',
      article_ids: articleIds,
      voucher_definition_uuid: c.voucher_definition_uuid || null,
      voucher_definition_uuids: voucherUuids,
      locked_addition_ids: normalizeLockedAdditionIds(
        articleIds,
        voucherUuids,
        c.locked_addition_ids,
      ),
    }
  })
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
  const articleIds = [...(c.article_ids || [])]
  cellEdit.value = {
    label: c.label || '',
    color: c.color || '#eeeeee',
    article_ids: articleIds,
    voucher_definition_uuid: vUuids[0] || null,
    voucher_definition_uuids: [...vUuids],
    locked_addition_ids: normalizeLockedAdditionIds(
      articleIds,
      vUuids,
      c.locked_addition_ids,
    ),
  }
  cellTreeSelection.value = articleIdsToTreeSelection(c.article_ids)
  cellDialogVisible.value = true

  if (cellCanHaveLockedAdditions(articleIds, vUuids) && articleIds[0] != null) {
    void loadLockedAdditionsForArticle(articleIds[0])
  } else {
    clearLockedAdditionsUi()
    cellEdit.value.locked_addition_ids = []
  }

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
    c.locked_addition_ids = updated.locked_addition_ids
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

watch(
  [cellTreeSelection, () => cellEdit.value.voucher_definition_uuids],
  ([selection, voucherUuids], previous) => {
    if (!cellDialogVisible.value) return
    const articleIds = treeSelectionToArticleIds(selection || [])
    const vUuids = Array.isArray(voucherUuids) ? voucherUuids.map(String) : []
    // Durable non-combo: vouchers or multiple articles — clear selected locks.
    if (vUuids.length > 0 || articleIds.length > 1) {
      clearLockedAdditionsUi()
      return
    }
    // Transient empty tree selection (mount/reload): keep seeded ids, only idle options.
    if (articleIds.length === 0) {
      clearLockedAdditionOptions()
      return
    }
    const articleId = articleIds[0]
    const prevSelection = previous?.[0]
    const prevArticleIds = treeSelectionToArticleIds(prevSelection || [])
    if (prevArticleIds.length === 1 && prevArticleIds[0] !== articleId) {
      clearLockedAdditionIds()
    }
    void loadLockedAdditionsForArticle(articleId)
  },
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
  touch-action: none;
  user-select: none;
}

.grid-cell--filled {
  cursor: grab;
}

.grid-cell--dragging-source {
  opacity: 0.45;
  cursor: grabbing;
}

.grid-cell--drop-target {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: 1px;
}

.grid-cell--drop-blocked {
  cursor: not-allowed;
  outline: 2px solid rgba(var(--v-theme-error), 0.7);
  outline-offset: 1px;
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

.locked-additions-list {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  max-height: 200px;
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
