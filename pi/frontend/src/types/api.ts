import type { components, paths } from './api.generated'

export type { components, paths }

export type EdgeBundleResponse = components['schemas']['EdgeBundleContract']
export type EdgeBundleEvent = components['schemas']['EdgeBundleEvent']
export type EdgeBundleArticle = components['schemas']['EdgeBundleArticle']
export type EdgeBundleArticleAddition = components['schemas']['EdgeBundleArticleAddition']
export type EdgeEventConfiguration = components['schemas']['EdgeEventConfiguration']
export type EdgeStationConfig = components['schemas']['EdgeStationConfig']

export type OrderLineIn = components['schemas']['OrderLineIn']
export type LineAdditionIn = components['schemas']['LineAdditionIn']
export type PaymentIn = components['schemas']['PaymentIn']
export type DiscountIn = components['schemas']['DiscountIn']

export type LocalOrderCreate = components['schemas']['LocalOrderCreate']
export type LocalOrderCreatedResponse = components['schemas']['LocalOrderCreatedResponse']
export type OrderPayResponse = components['schemas']['OrderPayResponse']
export type SyncStatusResponse = components['schemas']['SyncStatusResponse']
export type AccountSummaryResponse = components['schemas']['AccountSummaryResponse']
export type OpenOrderEntry = components['schemas']['OpenOrderEntry']
export type LineGroupEntry = components['schemas']['LineGroupEntry']
export type RegisterDisplayPayload = components['schemas']['RegisterDisplayPayload']
export type ShiftSessionRead = components['schemas']['ShiftSessionRead']
export type SetupStatusResponse = components['schemas']['SetupStatusResponse']
export type PaymentReceiptEscposResponse = components['schemas']['PaymentReceiptEscposResponse']
export type CloudReachableResponse = components['schemas']['CloudReachableResponse']
export type EmulatedReceiptSummary = components['schemas']['EmulatedReceiptSummary']
export type PreviewLine = components['schemas']['PreviewLine']
export type CollectiveBillListItem = components['schemas']['CollectiveBillListItem']
export type OpenCollectiveBillsResponse = components['schemas']['OpenCollectiveBillsResponse']
export type AssignCollectiveResponse = components['schemas']['AssignCollectiveResponse']
export type LineSelection = components['schemas']['LineSelection']
export type PositionCommentPreset = components['schemas']['PositionCommentPreset']
export type PrintJobSummary = components['schemas']['PrintJobSummary']
export type OpenTablesResponse = components['schemas']['OpenTablesResponse']
export type OpenTableRow = components['schemas']['OpenTableRow']
export type CollectiveBillCreatedResponse = components['schemas']['CollectiveBillCreatedResponse']
export type KitchenOrdersResponse = components['schemas']['KitchenOrdersResponse']
export type KitchenOrderTicket = components['schemas']['KitchenOrderTicket']
export type KitchenTicketLineEntry = components['schemas']['KitchenTicketLineEntry']
export type KitchenTicketPrintResponse = components['schemas']['KitchenTicketPrintResponse']
export type PickupOrdersResponse = components['schemas']['PickupOrdersResponse']
export type PickupOrderItem = components['schemas']['PickupOrderItem']
export type PaymentsListResponse = components['schemas']['PaymentsListResponse']
export type PaymentListItem = components['schemas']['PaymentListItem']
export type RegisterDisplayResponse = components['schemas']['RegisterDisplayResponse']
export type PrinterTestStationPrintsResponse = components['schemas']['PrinterTestStationPrintsResponse']
export type StationTestPrintResult = components['schemas']['StationTestPrintResult']
export type TablePartialSettleResponse = components['schemas']['TablePartialSettleResponse']
export type AdminStatusResponse = components['schemas']['AdminStatusResponse']

export interface ApiError extends Error {
  status?: number
  detail?: unknown
}

export function isApiError(err: unknown): err is ApiError {
  return err instanceof Error && 'status' in err
}

export function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) return error.message
  return fallback
}
