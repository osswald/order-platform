import { describe, expect, it } from 'vitest'
import { labelFromNameIfEmpty } from './articleLabelFromName'

describe('labelFromNameIfEmpty', () => {
  it('copies name trimmed to 21 when label empty', () => {
    expect(labelFromNameIfEmpty('abcdefghijklmnopqrstuvwxyz', '')).toBe('abcdefghijklmnopqrstu')
  })

  it('keeps existing label', () => {
    expect(labelFromNameIfEmpty('Catalog name', 'Hell 0.5')).toBe('Hell 0.5')
  })
})
