import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { describe, it } from 'node:test'
import { fileURLToPath } from 'node:url'

import { validateInquiryFields } from './inquiryValidation.js'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')

describe('validateInquiryFields', () => {
  it('accepts a complete payload', () => {
    assert.equal(
      validateInquiryFields({
        name: 'Anna',
        organisation: 'Festverein',
        email: 'anna@example.com',
        timeframe: 'August 2026',
        message: 'Bitte um Offerte',
      }),
      null,
    )
  })

  it('rejects missing required fields', () => {
    assert.match(
      validateInquiryFields({
        name: 'Anna',
        organisation: 'Festverein',
        email: 'anna@example.com',
        timeframe: '',
        message: 'Hallo',
      }),
      /Pflichtfelder/,
    )
  })

  it('rejects invalid email', () => {
    assert.match(
      validateInquiryFields({
        name: 'Anna',
        organisation: 'Festverein',
        email: 'not-valid',
        timeframe: 'August',
        message: 'Hallo',
      }),
      /E-Mail/,
    )
  })
})

describe('kontakt form markup', () => {
  const html = readFileSync(join(root, 'kontakt/index.html'), 'utf8')

  it('includes required fields and honeypot', () => {
    for (const name of ['name', 'organisation', 'email', 'phone', 'timeframe', 'message', 'website']) {
      assert.match(html, new RegExp(`name="${name}"`))
    }
    assert.match(html, /Datenschutz/)
    assert.match(html, /id="rental-inquiry-form"/)
  })
})

describe('marketing pages exist', () => {
  for (const page of ['index.html', 'ablauf/index.html', 'funktionen/index.html', 'kontakt/index.html']) {
    it(`has ${page}`, () => {
      const html = readFileSync(join(root, page), 'utf8')
      assert.match(html, /lang="de"/)
      assert.match(html, /Vendiqo/)
    })
  }
})
