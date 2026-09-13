import type { EventLayoutCellLocal, EventLayoutLocal } from '@/types/ui'
import { cellVoucherUuidsForPayload } from './eventConfigLayoutsPayload'

/** Pixel movement before a pointer gesture becomes a drag (vs click). */
export const LAYOUT_CELL_DRAG_THRESHOLD_PX = 8

/** True when the layout editor treats the slot as having content (drag source / occupied). */
export function layoutCellHasEditorData(c: EventLayoutCellLocal | null | undefined): boolean {
  if (!c) return false
  if ((c.label || '').trim()) return true
  if ((c.article_ids || []).length > 0) return true
  if (cellVoucherUuidsForPayload(c).length > 0) return true
  const color = (c.color || '').toLowerCase()
  if (color && color !== '#eeeeee' && color !== '#eee') return true
  return false
}

export type MoveLayoutCellResult = 'moved' | 'noop' | 'rejected'

/**
 * Move a filled cell to an empty grid slot by rewriting row/col.
 * Rejects occupied targets, out-of-bounds, empty sources; same slot is a no-op.
 */
export function moveLayoutCell(
  layout: EventLayoutLocal,
  fromRow: number,
  fromCol: number,
  toRow: number,
  toCol: number,
): MoveLayoutCellResult {
  if (fromRow === toRow && fromCol === toCol) return 'noop'

  const width = layout.grid_width
  const height = layout.grid_height
  if (
    toRow < 0 ||
    toCol < 0 ||
    toRow >= height ||
    toCol >= width ||
    fromRow < 0 ||
    fromCol < 0 ||
    fromRow >= height ||
    fromCol >= width
  ) {
    return 'rejected'
  }

  if (!Array.isArray(layout.cells)) layout.cells = []

  const source = layout.cells.find((c) => c.row === fromRow && c.col === fromCol)
  if (!source || !layoutCellHasEditorData(source)) return 'rejected'

  const target = layout.cells.find((c) => c.row === toRow && c.col === toCol)
  if (target && layoutCellHasEditorData(target)) return 'rejected'

  // Drop empty placeholder cells at the target so we don't leave duplicates.
  if (target) {
    layout.cells = layout.cells.filter((c) => !(c.row === toRow && c.col === toCol))
  }

  source.row = toRow
  source.col = toCol
  return 'moved'
}
