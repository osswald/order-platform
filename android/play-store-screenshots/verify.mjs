#!/usr/bin/env node
/**
 * Verify committed Play Store tablet screenshots meet size rules.
 */
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import {
  EXPECTED_VIEWPORTS,
  SCREENSHOT_SLUGS,
  pngDimensions,
  validatePlayTabletSize,
} from './pngMeta.mjs'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
let failed = 0

for (const sizeKey of /** @type {const} */ (['10in', '7in'])) {
  const vp = EXPECTED_VIEWPORTS[sizeKey]
  for (const slug of SCREENSHOT_SLUGS) {
    const name = `${sizeKey}-${slug}.png`
    const file = path.join(__dirname, name)
    if (!fs.existsSync(file)) {
      console.error(`MISSING ${name}`)
      failed++
      continue
    }
    const dim = pngDimensions(fs.readFileSync(file))
    const check = validatePlayTabletSize(sizeKey, dim.width, dim.height)
    const sizeOk = dim.width === vp.width && dim.height === vp.height
    const bytes = fs.statSync(file).size
    const mb = (bytes / (1024 * 1024)).toFixed(2)
    if (!check.ok || !sizeOk || bytes > 8 * 1024 * 1024) {
      console.error(
        `FAIL ${name} ${dim.width}x${dim.height} ${mb}MB ${check.reason || ''}`.trim(),
      )
      failed++
    } else {
      console.log(`OK   ${name} ${dim.width}x${dim.height} ${mb}MB`)
    }
  }
}

if (failed) {
  console.error(`\n${failed} file(s) failed verification`)
  process.exit(1)
}
console.log('\nAll screenshots OK')
