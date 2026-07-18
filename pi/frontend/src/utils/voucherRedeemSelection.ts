import type { EdgeBundleArticle, LineSelection } from '@/types/api'
import { lineAdditionLabels } from './bundleHelpers'

/** LineSelection narrowed to a redeemable article entitlement target. */
export type ArticleLineSelection = Omit<LineSelection, 'article_id'> & {
  article_id: number
}

export function isArticleLineSelection(sel: LineSelection): sel is ArticleLineSelection {
  return sel.article_id != null && Number.isFinite(Number(sel.article_id))
}

/** Return an article selection with a numeric article_id, or null if not redeemable. */
export function asArticleLineSelection(sel: LineSelection): ArticleLineSelection | null {
  if (!isArticleLineSelection(sel)) return null
  return { ...sel, article_id: Number(sel.article_id) }
}

export function voucherRedeemSelectionLabel(
  sel: { article_id: number; additions?: ArticleLineSelection['additions'] },
  arts: Record<string, EdgeBundleArticle>,
): string {
  const a = arts[String(sel.article_id)] || arts[sel.article_id as unknown as string]
  const base = a?.name || `Artikel #${sel.article_id}`
  const adds = lineAdditionLabels(sel, arts)
  if (!adds.length) return base
  const hint = adds.map((x) => x.name).join(', ')
  return `${base} (+ ${hint})`
}
