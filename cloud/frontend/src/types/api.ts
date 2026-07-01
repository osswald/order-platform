import type { components, paths } from './api.generated'

export type { components, paths }

export type CountryRead = components['schemas']['CountryRead']
export type CountryCreate = components['schemas']['CountryCreate']
export type CountryUpdate = components['schemas']['CountryUpdate']

export type HireCompanyRead = components['schemas']['HireCompanyRead']
export type HireCompanyCreate = components['schemas']['HireCompanyCreate']
export type HireCompanyUpdate = components['schemas']['HireCompanyUpdate']

export type OrganisationRead = components['schemas']['OrganisationRead']
export type OrganisationCreate = components['schemas']['OrganisationCreate']
export type OrganisationUpdate = components['schemas']['OrganisationUpdate']
export type ColorPaletteEntry = components['schemas']['ColorPaletteEntry']
export type ColorPaletteRead = components['schemas']['ColorPaletteRead']
export type ColorPaletteUpdate = components['schemas']['ColorPaletteUpdate']

export type UserRead = components['schemas']['UserRead']
export type UserCreate = components['schemas']['UserCreate']
export type UserUpdate = components['schemas']['UserUpdate']

export type EventRead = components['schemas']['EventRead'] & {
  has_twint_qr?: boolean
  organisation_currency?: string
}
export type EventCreate = components['schemas']['EventCreate']
export type EventUpdate = components['schemas']['EventUpdate']
export type EventCopyIn = components['schemas']['EventCopyIn']
export type EventConfigurationRead = components['schemas']['EventConfigurationRead']
export type EventConfigurationIn = components['schemas']['EventConfigurationIn']
export type EventCashSessionsPageRead = components['schemas']['EventCashSessionsPageRead']
export type EventCollectiveBillsListRead = components['schemas']['EventCollectiveBillsListRead']
export type EventSalesReportV3Read = components['schemas']['EventSalesReportV3Read']
export type EventStatsRead = components['schemas']['EventStatsRead']
export type EventStockListRead = components['schemas']['EventStockListRead']
export type EventStockUpdateIn = components['schemas']['EventStockUpdateIn']
export type EventTransactionsPageRead = components['schemas']['EventTransactionsPageRead']
export type CashSessionRead = components['schemas']['CashSessionRead']
export type CollectiveBillRead = components['schemas']['CollectiveBillRead']
export type TransactionRead = components['schemas']['TransactionRead']
export type PrinterOptionRead = components['schemas']['PrinterOptionRead']
export type StationConfigIn = components['schemas']['StationConfigIn']
export type EventWaiterConfigIn = components['schemas']['EventWaiterConfigIn']
export type AppLayoutIn = components['schemas']['AppLayoutIn']
export type CashRegisterIn = components['schemas']['CashRegisterIn']
export type VoucherDefinitionIn = components['schemas']['VoucherDefinitionIn']
export type KitchenMonitorPrinterIn = components['schemas']['KitchenMonitorPrinterIn']
export type ArticleCategoryCreate = components['schemas']['ArticleCategoryCreate']
export type ArticleCategoryUpdate = components['schemas']['ArticleCategoryUpdate']
export type ArticleCreate = components['schemas']['ArticleCreate']
export type ArticleUpdate = components['schemas']['ArticleUpdate']

export type ArticleRead = components['schemas']['ArticleRead']
export type ArticleCategoryRead = components['schemas']['ArticleCategoryRead']
export type ArticleAdditionsRead = components['schemas']['ArticleAdditionsRead']
export type WaiterRead = components['schemas']['WaiterRead']
export type ApplianceRead = components['schemas']['ApplianceRead']
export type ApplianceUpdate = components['schemas']['ApplianceUpdate']
export type AppliancePairingSessionRead = components['schemas']['AppliancePairingSessionRead']
export type OrgApplianceLendingItem = components['schemas']['OrgApplianceLendingItem']
export type OrganisationApplianceLendingsRead = components['schemas']['OrganisationApplianceLendingsRead']
export type PaymentTypeRead = components['schemas']['PaymentTypeRead']
export type PaymentTypeAccountDefaultRead = components['schemas']['PaymentTypeAccountDefaultRead']
export type TaxCodeRead = components['schemas']['TaxCodeRead']
export type TaxCodeAccountDefaultRead = components['schemas']['TaxCodeAccountDefaultRead']
export type AccountingAccountRead = components['schemas']['AccountingAccountRead']
export type AccountingAccountCreate = components['schemas']['AccountingAccountCreate']
export type AccountingAccountUpdate = components['schemas']['AccountingAccountUpdate']
export type HostedPiRead = components['schemas']['HostedPiRead']
export type HireCompanyBrief = components['schemas']['HireCompanyBrief']
export type ReceiptPrintingRead = components['schemas']['ReceiptPrintingRead']
export type EventReceiptPrintingConfig = components['schemas']['EventReceiptPrintingConfig']
export type ReceiptPrintingConfig = components['schemas']['ReceiptPrintingConfig']
export type PositionCommentPresetRead = components['schemas']['PositionCommentPresetRead']
export type StripeConnectStatus = components['schemas']['StripeConnectStatus']
export type StripeAccountLinkResponse = components['schemas']['StripeAccountLinkResponse']
export type TaxCodeRateRead = components['schemas']['TaxCodeRateRead']

export type TokenResponse = components['schemas']['Token']
export type AuthMeResponse = components['schemas']['MeResponse']
export type AuthMeUpdate = components['schemas']['MeUpdate']

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
