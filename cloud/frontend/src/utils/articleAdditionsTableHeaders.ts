import type { DataTableHeader } from '@/types/vuetify'

type Translate = (key: string) => string

/** Nested additions table headers for article detail (Vorauswahl Pi + kitchen combine). */
export function articleAdditionsTableHeaders(t: Translate): DataTableHeader[] {
  return [
    { title: t('articles.additionColumn'), key: 'name' },
    { title: t('common.price'), key: 'price', sortable: false },
    { title: t('articles.preselectedColumn'), key: 'preselected', sortable: false, align: 'center', width: 120 },
    {
      title: t('articles.combineOnKitchenDisplayColumn'),
      key: 'combine_on_kitchen_display',
      sortable: false,
      align: 'center',
      width: 160,
    },
    { title: '', key: 'actions', sortable: false, align: 'end', width: 56 },
  ]
}
