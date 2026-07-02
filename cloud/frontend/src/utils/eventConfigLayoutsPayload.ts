import type { AppLayoutIn } from '@/types/api'
import type { EventLayoutLocal } from '@/types/ui'

type LayoutCellLike = {
  row: number
  col: number
  label?: string | null
  color?: string | null
  article_ids?: number[] | null
  voucher_definition_uuid?: string | null
  voucher_definition_uuids?: string[] | null
}

type LayoutLike = {
  uuid?: string | null
  name?: string | null
  is_default?: boolean | null
  grid_width: number
  grid_height: number
  cells?: LayoutCellLike[] | null
}

/** Server layouts only need uuid + cells for merge-before-save. */
export type ServerLayoutCellsSource = Pick<LayoutLike, 'uuid' | 'cells'>

export function cellVoucherUuidsForPayload(cell: LayoutCellLike): string[] {
  const list = cell.voucher_definition_uuids
  if (Array.isArray(list) && list.length) return list.map(String)
  if (cell.voucher_definition_uuid) return [String(cell.voucher_definition_uuid)]
  return []
}

/** Matches backend layout_cell_requires_content: articles and/or vouchers required. */
export function layoutCellHasContent(cell: LayoutCellLike): boolean {
  const articleIds = Array.isArray(cell.article_ids) ? cell.article_ids : []
  if (articleIds.length > 0) return true
  return cellVoucherUuidsForPayload(cell).length > 0
}

export function isLayoutCellInGrid(
  cell: { row: number; col: number },
  width: number,
  height: number,
): boolean {
  return cell.row >= 0 && cell.col >= 0 && cell.row < height && cell.col < width
}

export function mapLayoutsToPutPayload(layouts: LayoutLike[]): AppLayoutIn[] {
  return layouts.map((layout) => ({
    uuid: layout.uuid ?? undefined,
    name: layout.name?.trim() || null,
    is_default: !!layout.is_default,
    grid_width: layout.grid_width,
    grid_height: layout.grid_height,
    cells: (layout.cells || [])
      .filter((cell) => isLayoutCellInGrid(cell, layout.grid_width, layout.grid_height))
      .filter((cell) => layoutCellHasContent(cell))
      .map((cell) => {
        const voucherUuids = cellVoucherUuidsForPayload(cell)
        return {
          row: cell.row,
          col: cell.col,
          label: cell.label || '',
          color: cell.color || '#eeeeee',
          article_ids: Array.isArray(cell.article_ids) ? cell.article_ids : [],
          voucher_definition_uuid: voucherUuids[0] || null,
          voucher_definition_uuids: voucherUuids,
        }
      }),
  }))
}

/**
 * Preserve server-side cells for existing layouts while keeping local-only rows
 * (e.g. a layout the user just added before cells finished loading).
 */
export function mergeLayoutsWithServerCells(
  layoutsLocal: EventLayoutLocal[],
  serverLayouts: readonly ServerLayoutCellsSource[],
): LayoutLike[] {
  const serverByUuid = new Map(
    (serverLayouts || []).map((layout) => [String(layout.uuid), layout]),
  )
  return layoutsLocal.map((local) => {
    const server = local.uuid ? serverByUuid.get(String(local.uuid)) : undefined
    if (!server) return local
    return {
      ...local,
      cells: server.cells || [],
    }
  })
}

/**
 * When the config page loads with ?fields=summary, layout cells are empty locally.
 * Autosave must not PUT those empty cells or the backend replaces all cells with [].
 */
export function resolveAppLayoutsForPut(options: {
  layoutsLocal: EventLayoutLocal[]
  layoutCellsLoaded: boolean
  serverLayouts?: readonly ServerLayoutCellsSource[] | null
}): AppLayoutIn[] {
  const { layoutsLocal, layoutCellsLoaded, serverLayouts } = options
  if (layoutCellsLoaded) {
    return mapLayoutsToPutPayload(layoutsLocal)
  }
  if (!serverLayouts?.length) {
    return mapLayoutsToPutPayload(layoutsLocal)
  }
  return mapLayoutsToPutPayload(mergeLayoutsWithServerCells(layoutsLocal, serverLayouts))
}
