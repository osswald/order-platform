import type { StockGroup } from './stockByStation'

interface StockRow {
  id?: number
  name?: string
  monitor_stock?: boolean
  in_stock?: number
  sellable?: boolean
  unit?: string | null
  ingredients?: Array<{ ingredient_id?: number; amount?: number }>
}

function sortByName(a: StockRow, b: StockRow): number {
  return String(a?.name || '').localeCompare(String(b?.name || ''), 'de')
}

export function hasRecipeIngredients(article: StockRow | null | undefined): boolean {
  return Array.isArray(article?.ingredients) && article.ingredients.length > 0
}

export function nonCompositeArticlesForStock(
  articles: Record<string, StockRow> | null | undefined,
): StockRow[] {
  if (!articles) return []
  return Object.values(articles).filter((a) => a && !hasRecipeIngredients(a))
}

export function ingredientStockGroup(
  ingredients: Record<string, StockRow> | null | undefined,
  { monitoredOnly = true }: { monitoredOnly?: boolean } = {},
): StockGroup | null {
  const rows = Object.values(ingredients || {}).filter(
    (row) => row && (!monitoredOnly || row.monitor_stock),
  )
  if (!rows.length) return null
  rows.sort(sortByName)
  return { key: 'ingredients', name: 'Zutaten', items: rows }
}

export function stockGroupsWithIngredientsForEvent(
  ev: {
    articles?: Record<string, StockRow>
    ingredients?: Record<string, StockRow>
    configuration?: { stations?: Array<{ uuid?: string; name?: string; sort_order?: number; article_ids?: number[] }> }
  } | null | undefined,
  stockGroupsForItems: (
    items: StockRow[] | null | undefined,
    stations: unknown,
    opts?: { monitoredOnly?: boolean },
  ) => StockGroup[],
  { monitoredOnly = true }: { monitoredOnly?: boolean } = {},
): StockGroup[] {
  const groups: StockGroup[] = []
  const ingGroup = ingredientStockGroup(ev?.ingredients, { monitoredOnly })
  if (ingGroup) groups.push(ingGroup)
  const articleRows = nonCompositeArticlesForStock(ev?.articles).filter(
    (row) => row && (!monitoredOnly || row.monitor_stock),
  )
  groups.push(...stockGroupsForItems(articleRows, ev?.configuration?.stations, { monitoredOnly }))
  return groups.filter((g) => g.items.length)
}
