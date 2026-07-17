import { describe, expect, it } from 'vitest'
import type { DataTableHeader } from '@/types/vuetify'
import {
  articleCategoryListHeaders,
  articleListHeaders,
  eventListHeaders,
  ingredientListHeaders,
  waiterListHeaders,
} from './orgScopedListTableHeaders'

const t = (key: string) => key

function headerKeys(headers: DataTableHeader[]): string[] {
  return headers.map((header) => header.key)
}

describe('orgScopedListTableHeaders', () => {
  it('article list headers omit organisation column', () => {
    expect(headerKeys(articleListHeaders(t))).not.toContain('organisation_name')
  })

  it('article category list headers omit organisation column', () => {
    expect(headerKeys(articleCategoryListHeaders(t))).not.toContain('organisation_name')
  })

  it('waiter list headers omit organisation column', () => {
    expect(headerKeys(waiterListHeaders(t))).not.toContain('organisation_name')
  })

  it('event list headers omit organisation column', () => {
    expect(headerKeys(eventListHeaders(t))).not.toContain('organisation_name')
  })

  it('ingredient list headers omit organisation column', () => {
    expect(headerKeys(ingredientListHeaders(t))).not.toContain('organisation_name')
  })
})
