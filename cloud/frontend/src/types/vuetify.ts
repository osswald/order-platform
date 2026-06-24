/** Vuetify data-table helpers for strict slot typing. */

export interface DataTableHeader<T extends string = string> {
  title: string
  key: T
  sortable?: boolean
  align?: 'start' | 'center' | 'end'
  width?: string | number
}

export interface DataTableSlotItem<T extends Record<string, unknown>> {
  item: T
  index: number
  columns: DataTableHeader[]
  isSelected: (item: T) => boolean
  toggleSelect: (item: T) => void
  internalItem: { value: unknown; raw: T }
}

export type SlotItem<T extends Record<string, unknown>> = DataTableSlotItem<T>['item']

export type SlotProps<T extends Record<string, unknown>> = DataTableSlotItem<T>

export interface DataTableRowClickPayload<T> {
  item: T
  index: number
}

export interface DataTableServerOptions {
  page?: number
  itemsPerPage?: number
  sortBy?: Array<{ key: string; order?: 'asc' | 'desc' }>
}
