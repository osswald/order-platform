import type { OrganisationRead } from './api'

export type SaveStatus = 'idle' | 'dirty' | 'saving' | 'saved' | 'error'

export interface EventStammdatenForm {
  name: string
  status: string
  start: Date | null
  end: Date | null
  paymentMode: string
  paymentTypes: string[]
  instantCollectiveBillName: string
  offerPaymentReceipt: boolean
  cashRegistersEnabled: boolean
  shiftSettlementEnabled: boolean
  vouchersEnabled: boolean
  alternativePrintersEnabled: boolean
  kitchenMonitorsEnabled: boolean
  discountsEnabled: boolean
}

export interface EventPrinterRuleLocal {
  sort_order?: number
  rule_type: string
  table_from: number | null
  table_to: number | null
  pickup_prefix: string
  printer_appliance_id: number | null
}

export interface EventStationLocal {
  uuid?: string | null
  name: string
  printer_appliance_id: number | null
  printer_rules: EventPrinterRuleLocal[]
  article_ids: number[]
}

export interface EventKitchenMonitorLocal {
  printer_appliance_id: number | null
  sort_order?: number
  label: string
}

export interface EventWaiterLocal {
  _key?: string
  uuid?: string | null
  name: string
  pin: string
  source_waiter_id?: number | null
  subsidiary_code?: string
}

export interface EventLayoutCellLocal {
  row: number
  col: number
  label: string
  color: string
  article_ids: number[]
  voucher_definition_uuid: string | null
  voucher_definition_uuids: string[]
}

export interface EventLayoutLocal {
  uuid: string
  name: string
  is_default: boolean
  grid_width: number
  grid_height: number
  cells: EventLayoutCellLocal[]
}

export interface EventCashRegisterLocal {
  uuid?: string | null
  name: string
  pickup_code_prefix: string
  pin: string
  layout_uuid: string
  receipt_printer_appliance_id: number | null
  subsidiary_code?: string
}

export interface EventVoucherDefinitionLocal {
  uuid: string
  name: string
  kind: string
  value_amount: number
  allowed_article_ids: number[]
  include_additions: boolean
}

export interface EventCellEditState {
  label: string
  color: string
  article_ids: number[]
  voucher_definition_uuid: string | null
  voucher_definition_uuids: string[]
}

export interface LayoutOption {
  name: string
  value: string
}

export interface ArticleSelectOption {
  name: string
  value: number
}

export interface StatusChangePayload {
  status: SaveStatus
  errorMessage?: string
}

export interface LayoutRemovedPayload {
  removedUuid: string
  fallbackUuid: string
}

export interface StationArticleTreeNode {
  key: string
  label: string
  children?: StationArticleTreeNode[]
}

export interface StationArticleTreeResponse {
  nodes?: StationArticleTreeNode[]
}

export interface BookkeepingAccountRef {
  number: string
  name: string
}

export interface BookkeepingTaxCodeRef {
  name: string
  rate_percent?: number | null
}

export interface BookkeepingSummaryRow {
  debit_account?: BookkeepingAccountRef | null
  credit_account?: BookkeepingAccountRef | null
  tax_code?: BookkeepingTaxCodeRef | null
  net_cents: number
  vat_cents: number
  gross_cents: number
  subsidiary_code?: string | null
  subsidiary_name?: string | null
  collective_bill_name?: string | null
}

export interface BookkeepingDetailLine {
  side: string
  account?: BookkeepingAccountRef | null
  amount_cents: number
  tax_code?: BookkeepingTaxCodeRef | null
  subsidiary_code?: string | null
  subsidiary_name?: string | null
}

export interface BookkeepingDetailEntry {
  kind: string
  payment_id?: number | null
  submission_id?: number | null
  collective_bill_uuid?: string | null
  method?: string
  method_label?: string
  amount_cents?: number
  collective_bill_name?: string | null
  lines?: BookkeepingDetailLine[]
}

export interface EventBookkeepingReport {
  warnings?: string[]
  summary?: BookkeepingSummaryRow[]
  detail?: BookkeepingDetailEntry[]
  currency?: string
  error?: string
}

export interface CollectiveBillLineGroup {
  article_id?: number
  name?: string
  additions?: { article_id: number; name: string }[]
  total_qty?: number
  line_total_cents?: number
}

export interface CollectiveBillPositionRow {
  rowKey: string
  name: string
  additions: { article_id: number; name: string }[]
  qty: number
  line_cents: number
}

export interface CashSessionLedgerRow {
  entry_type: string
  method?: string | null
  voucher_name?: string | null
  amount_cents: number
}

export interface EventStockItemLocal {
  id: number
  name: string
  label: string
  monitor_stock: boolean
  in_stock: number
}

export interface TransactionLineLocal {
  name: string
  qty: number
  line_cents: number
  additions?: { article_id: number; name: string }[]
  transfer_note?: string
}

export interface OrganisationStammdatenForm {
  name: string
  address: string
  zip: string
  city: string
  countryId: number | null
  currency: string
  userIdsArray: number[]
}

export interface SelectOption<T = string | number> {
  label: string
  value: T
  title?: string
}

export interface SectionNavSection {
  id: string
  title: string
  defaultOpen?: boolean
}

export interface PaymentTypeForm {
  slug: string
  sortOrder: number
  isActive: boolean
}

export interface TaxCodeRateForm {
  ratePercent: number | null
  validFrom: string
  validTo: string
}

export interface TaxCodeForm {
  name: string
  countryId: number | null
  rates: TaxCodeRateForm[]
}

export interface WaiterForm {
  name: string
  pin: string
}

export interface UserForm {
  name: string
  email: string
  role: string
  password: string
  organisationIdsArray: number[]
  eventAdminPin: string
  hasEventAdminPin: boolean
  clearEventAdminPin: boolean
}

export interface TenantSettingsForm {
  name: string
  address: string
  zip: string
  city: string
  countryId: number | null
}

export interface ReceiptProfileFieldsModel {
  logo_enabled: boolean
  show_event_title: boolean
  size_table_or_pickup: string
  size_order_lines: string
  show_price?: boolean
  bottom_line: string
}

export interface PaymentReceiptProfileModel {
  logo_enabled: boolean
  show_event_title: boolean
  size_order_lines: string
  bottom_line: string
}

export interface ReceiptPrintingFormConfig {
  station_receipt: ReceiptProfileFieldsModel
  customer_receipt: ReceiptProfileFieldsModel
  payment_receipt: PaymentReceiptProfileModel
  label_event_title?: string
}

/** Subset returned by GET /events/organisations for session org picker. */
export interface AccessibleOrganisation {
  id: number
  name: string
  currency: string
  country_id: number
  vat_liable: boolean
  default_tax_code_id: number | null
  accounts_enabled: boolean
}

export interface DashboardAttentionItem {
  type: string
  event_id: number
  event_name: string
}

export interface DashboardSalesEventRow {
  event_id: number
  name: string
  start: string
  end: string
  distinct_orders_count: number
  line_cents: number
  open_cents: number
}

export interface DashboardSummary {
  organisation_id: number
  organisation_name: string
  events_by_status: Record<string, number>
  running_event_ids: number[]
  running_events_count: number
  events_total: number
  catalog: {
    waiters: number
    articles: number
    categories: number
  }
  lendings: {
    current: number
    planned: number
  }
  attention: DashboardAttentionItem[]
  sales: {
    currency: string
    totals: {
      distinct_orders_count: number
      line_cents: number
      paid_cents: number
      open_cents: number
    }
    by_event: DashboardSalesEventRow[]
  }
}

export interface ArticleForm {
  name: string
  label: string
  importArticleNumber: string
  description: string
  unit: string
  accountingAccountId: number | null
  taxCodeId: number | null
  price: number
  isAddition: boolean
  isActive: boolean
  articleCategoryId: number | null
}
export interface AdditionLinkLocal {
  addition_article_id: number
  name: string
  price: number
  sort_order: number
  preselected: boolean
}

export interface ArticleCategoryForm {
  name: string
  accountingAccountId: number | null
  organisation_id?: number
}

export interface ApplianceFormState {
  type: string
  name: string
  ip_address: string
  escpos_feed_lines: number
  model: string
  comment: string
}

export interface LendFormState {
  organisationId: number | null
  startDate: Date | null
  endDate: Date | null
}

export interface HelpArticleBody {
  title: string
  summary: string
  html: string
  slug: string
  categoryId: string
  categoryTitle: string
}

export interface SessionContext {
  accessibleOrganisations: { value: OrganisationRead[] }
  reloadHireCompaniesAndSelect: (companyId?: number | null) => Promise<void>
  reloadOrganisationsAndSelect: (organisationId?: number | null) => Promise<void>
  fetchAccessibleOrganisations?: () => Promise<void>
  activeHireCompanyId?: { value: number | null }
}

export interface OrganisationPickerEntry {
  id: number
  name?: string | null
  city?: string | null
  country?: { name?: string | null } | null
}

export interface LendingSubmitFailure {
  name: string
  detail: string
}
