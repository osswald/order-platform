import type { AppLayoutIn, EventConfigurationRead } from '@/types/api'
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

export function cellVoucherUuidsForPayload(cell: LayoutCellLike): string[] {
  const list = cell.voucher_definition_uuids
  if (Array.isArray(list) && list.length) return list.map(String)
  if (cell.voucher_definition_uuid) return [String(cell.voucher_definition_uuid)]
  return []
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
 * When the config page loads with ?fields=summary, layout cells are empty locally.
 * Autosave must not PUT those empty cells or the backend replaces all cells with [].
 */
export function resolveAppLayoutsForPut(options: {
  layoutsLocal: EventLayoutLocal[]
  layoutCellsLoaded: boolean
  serverLayouts?: EventConfigurationRead['app_layouts'] | null
}): AppLayoutIn[] {
  const { layoutsLocal, layoutCellsLoaded, serverLayouts } = options
  if (!layoutCellsLoaded && serverLayouts?.length) {
    return mapLayoutsToPutPayload(serverLayouts)
  }
  return mapLayoutsToPutPayload(layoutsLocal)
}
