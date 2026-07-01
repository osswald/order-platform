import { describe, expect, it } from 'vitest'
import { formatStockInsufficientMessage } from './stockError'

describe('formatStockInsufficientMessage', () => {
  it('formats single line issue', () => {
    const msg = formatStockInsufficientMessage([
      {
        article_name: 'Pizza',
        requested_qty: 5,
        max_orderable_qty: 3,
        limiting_name: 'Tomaten',
      },
    ])
    expect(msg).toContain('Pizza')
    expect(msg).toContain('3')
    expect(msg).toContain('Tomaten')
  })

  it('formats multiple issues', () => {
    const msg = formatStockInsufficientMessage([
      { article_name: 'Pizza', requested_qty: 2, max_orderable_qty: 1 },
      { article_name: 'Salat', requested_qty: 4, max_orderable_qty: 2 },
    ])
    expect(msg).toContain('Bestand nicht ausreichend')
    expect(msg).toContain('Pizza')
    expect(msg).toContain('Salat')
  })

  it('formats addition ingredient issues', () => {
    const msg = formatStockInsufficientMessage([
      {
        article_name: 'Burger',
        addition_name: 'Extra Käse',
        requested_qty: 3,
        max_orderable_qty: 1,
        reason: 'addition_ingredient',
        limiting_name: 'Käse',
      },
    ])
    expect(msg).toContain('Burger')
    expect(msg).toContain('Extra Käse')
    expect(msg).toContain('Käse')
  })

  it('formats order-level shared ingredient shortfall', () => {
    const msg = formatStockInsufficientMessage([
      {
        line_index: -1,
        article_name: 'Kartoffelsalat',
        requested_qty: 30.5,
        max_orderable_qty: 30,
        reason: 'ingredient',
        limiting_name: 'Kartoffelsalat',
      },
    ])
    expect(msg).toContain('30.5 benötigt')
    expect(msg).toContain('nur 30 verfügbar')
    expect(msg).toContain('Kartoffelsalat')
  })
})
