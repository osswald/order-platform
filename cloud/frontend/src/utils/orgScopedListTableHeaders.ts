import type { DataTableHeader } from '@/types/vuetify'

type TranslateFn = (key: string) => string

export function articleListHeaders(t: TranslateFn): DataTableHeader[] {
  return [
    { title: t('common.id'), key: 'id' },
    { title: t('common.type'), key: 'is_addition', sortable: false },
    { title: t('articles.isActive'), key: 'is_active', sortable: false },
    { title: t('common.name'), key: 'name' },
    { title: t('articles.importNumberShort'), key: 'import_article_number' },
    { title: t('common.label'), key: 'label' },
    { title: t('common.unit'), key: 'unit' },
    { title: t('common.price'), key: 'price', sortable: false },
    { title: t('common.category'), key: 'article_category_name' },
    { title: t('common.actions'), key: 'actions', sortable: false, align: 'end' },
  ]
}

export function articleCategoryListHeaders(t: TranslateFn): DataTableHeader[] {
  return [
    { title: t('common.id'), key: 'id' },
    { title: t('common.name'), key: 'name' },
    { title: t('articleCategories.articlesCount'), key: 'article_count' },
    { title: t('common.actions'), key: 'actions', sortable: false, align: 'end' },
  ]
}

export function waiterListHeaders(t: TranslateFn): DataTableHeader[] {
  return [
    { title: t('common.id'), key: 'id' },
    { title: t('common.name'), key: 'name' },
    { title: t('common.pin'), key: 'pin' },
    { title: t('common.actions'), key: 'actions', sortable: false, align: 'end' },
  ]
}

export function ingredientListHeaders(t: TranslateFn): DataTableHeader[] {
  return [
    { title: t('common.id'), key: 'id' },
    { title: t('common.name'), key: 'name' },
    { title: t('common.unit'), key: 'unit' },
    { title: t('ingredients.isActive'), key: 'is_active', sortable: false },
    { title: t('ingredients.usageCount'), key: 'usage_count' },
    { title: t('common.actions'), key: 'actions', sortable: false, align: 'end' },
  ]
}

export function eventListHeaders(t: TranslateFn): DataTableHeader[] {
  return [
    { title: t('events.table.id'), key: 'id' },
    { title: t('events.table.name'), key: 'name' },
    { title: t('events.table.status'), key: 'status', sortable: false },
    { title: t('events.table.start'), key: 'start', sortable: false },
    { title: t('events.table.end'), key: 'end', sortable: false },
    { title: t('events.table.actions'), key: 'actions', sortable: false, align: 'end', width: '8rem' },
  ]
}
