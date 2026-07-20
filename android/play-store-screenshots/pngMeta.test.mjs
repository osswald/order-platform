import assert from 'node:assert/strict'
import test from 'node:test'
import {
  EXPECTED_VIEWPORTS,
  SCREENSHOT_SLUGS,
  pngDimensions,
  validatePlayTabletSize,
} from './pngMeta.mjs'

test('pngDimensions reads IHDR width and height', () => {
  // Minimal valid PNG signature + IHDR with 1280x720
  const buf = Buffer.alloc(24)
  buf[0] = 0x89
  buf.write('PNG', 1, 'ascii')
  buf.writeUInt32BE(1280, 16)
  buf.writeUInt32BE(720, 20)
  assert.deepEqual(pngDimensions(buf), { width: 1280, height: 720 })
})

test('validatePlayTabletSize accepts recommended 16:9 sizes', () => {
  assert.equal(validatePlayTabletSize('7in', 1280, 720).ok, true)
  assert.equal(validatePlayTabletSize('10in', 1920, 1080).ok, true)
})

test('validatePlayTabletSize rejects wrong aspect or out-of-range', () => {
  assert.equal(validatePlayTabletSize('7in', 1000, 1000).ok, false)
  assert.equal(validatePlayTabletSize('10in', 800, 450).ok, false)
})

test('screenshot naming covers the marketing set', () => {
  assert.equal(SCREENSHOT_SLUGS.length, 8)
  assert.deepEqual(EXPECTED_VIEWPORTS['10in'], { width: 1920, height: 1080 })
  assert.deepEqual(EXPECTED_VIEWPORTS['7in'], { width: 1280, height: 720 })
})
