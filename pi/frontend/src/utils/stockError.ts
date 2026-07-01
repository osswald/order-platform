export interface StockInsufficientIssue {
  line_index?: number
  article_id?: number
  article_name?: string
  requested_qty?: number
  max_orderable_qty?: number
  reason?: string
  limiting_name?: string | null
  addition_name?: string | null
}

export function extractStockInsufficientIssues(error: unknown): StockInsufficientIssue[] | null {
  if (!error || typeof error !== 'object') return null
  const detail = (error as { detail?: unknown }).detail
  if (!detail || typeof detail !== 'object') return null
  const body = detail as { detail?: { code?: string; issues?: StockInsufficientIssue[] } }
  const payload = body.detail ?? (detail as { code?: string; issues?: StockInsufficientIssue[] })
  if (payload?.code !== 'stock_insufficient' || !Array.isArray(payload.issues)) return null
  return payload.issues
}

export function formatStockInsufficientMessage(issues: StockInsufficientIssue[]): string {
  if (!issues.length) return 'Bestand nicht ausreichend.'
  const lines = issues.map((issue) => {
    const name = issue.article_name || `Artikel #${issue.article_id ?? '?'}`
    const requested = issue.requested_qty ?? '?'
    const max = issue.max_orderable_qty ?? 0
    const limit = issue.limiting_name ? ` (Engpass: ${issue.limiting_name})` : ''
    if (issue.line_index === -1 && issue.reason === 'ingredient') {
      return `«${name}»: ${requested} benötigt, nur ${max} verfügbar${limit}`
    }
    if (issue.reason === 'addition_ingredient' && issue.addition_name) {
      return `«${name}» / «${issue.addition_name}»: maximal ${max} statt ${requested} Stück bestellbar${limit}`
    }
    return `«${name}»: maximal ${max} statt ${requested} Stück bestellbar${limit}`
  })
  if (lines.length === 1) return lines[0]
  return `Bestand nicht ausreichend:\n${lines.join('\n')}`
}

export function stockInsufficientMessage(error: unknown, fallback = 'Bestand nicht ausreichend.'): string {
  const issues = extractStockInsufficientIssues(error)
  if (!issues?.length) return fallback
  return formatStockInsufficientMessage(issues)
}
