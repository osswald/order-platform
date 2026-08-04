import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { mdiIconPaths, resolveMdiIconPath } from './mdiIconPaths'

const SRC_ROOT = join(__dirname, '..')

function collectSourceFiles(dir: string, out: string[] = []): string[] {
  for (const name of readdirSync(dir)) {
    if (name === 'icons') continue
    const full = join(dir, name)
    const st = statSync(full)
    if (st.isDirectory()) {
      collectSourceFiles(full, out)
      continue
    }
    if (full.endsWith('.vue') || full.endsWith('.ts')) {
      out.push(full)
    }
  }
  return out
}

function extractMdiNames(source: string): string[] {
  const found = new Set<string>()
  for (const match of source.matchAll(/['"]?(mdi-[a-z0-9-]+)['"]?/g)) {
    found.add(match[1])
  }
  return [...found]
}

describe('mdiIconPaths', () => {
  it('resolves every mdi-* icon referenced outside src/icons', () => {
    const used = new Set<string>()
    for (const file of collectSourceFiles(SRC_ROOT)) {
      for (const name of extractMdiNames(readFileSync(file, 'utf8'))) {
        used.add(name)
      }
    }
    const missing = [...used].filter((name) => !resolveMdiIconPath(name)).sort()
    expect(missing, `missing icon paths: ${missing.join(', ')}`).toEqual([])
  })

  it('maps known icons to non-empty SVG path data', () => {
    expect(mdiIconPaths['mdi-magnify']?.length).toBeGreaterThan(10)
    expect(mdiIconPaths['mdi-help-circle-outline']?.length).toBeGreaterThan(10)
  })
})
